"""
Import all data from old production PostgreSQL database into dalia20.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  HOW TO RUN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  This command must run inside the Django web container (not on the host),
  because it needs the Django ORM, the internal Podman network to reach
  dalia20-db, and the pg_dump binary installed in the web container.

  Run via interactive shell:
      make bash
      python manage.py import_from_old_prod --dry-run
      python manage.py import_from_old_prod

  Or run directly from the host without entering the container:
      podman exec dalia20-web python manage.py import_from_old_prod --dry-run
      podman exec dalia20-web python manage.py import_from_old_prod

  Optional flags (append to the import command above as needed):

      --db-url postgresql://user:pass@host:5432/dbname
          Override the old-prod database connection string.
          Default: value of OLD_PROD_DB_URL environment variable
          Example: python manage.py import_from_old_prod --db-url postgresql://<USER>:<PASS>@<HOST>:<PORT>/<DB>

      --backup-dir /some/path
          Save the backup file to a different directory instead of /tmp.
          Example: python manage.py import_from_old_prod --backup-dir /app/backups

      --no-backup
          Skip the automatic database backup before importing.
          NOT recommended — only use if you have already made a manual backup.
          Example: python manage.py import_from_old_prod --no-backup

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  WHAT GETS IMPORTED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  1. Users (all, matched by email or username; unmatched created as inactive)
  2. Social accounts (OIDC tokens for NFDI AAI login)
  3. RelationTypeCategory + RelationType (vocabulary)
  4. Organizations
  5. Persons (user profiles — needed for preferences page)
  6. Resources (all)
  7. ResourceContent (all) with all M2M relations:
       disciplines, languages, learning_resource_types, licenses, media_types,
       file_formats, proficiency_levels, target_groups, organizations, people
  8. ResourceRelatedItem (related URLs)
  9. ResourceCommunityRelation (content ↔ community links)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  WHAT GETS BACKED UP AND WHY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  The backup uses pg_dump connecting to dalia20-db over the internal Podman
  network (host: db, port: 5432). This produces a complete SQL dump of the
  entire database — every table, every row, sequences, indexes.

  pg_dump is available in the web container (postgresql-client installed in
  the Dockerfile runtime stage).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  HOW TO RESTORE IF SOMETHING GOES WRONG
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  If the import fails mid-way, the atomic transaction automatically rolls back
  all changes — no manual restore is needed in that case.

  If the import succeeds but you decide to undo it afterwards:

      podman exec dalia20-web bash
      pg_restore -h db -U dalia20 -d dalia20 -c /tmp/db_backup_<timestamp>.dump

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  SAFETY GUARANTEES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  1. Backup is verified non-empty before any write begins — aborts on failure.
  2. All writes run inside a single transaction.atomic() — any error rolls back
     everything automatically.
  3. Idempotent: records that already exist (matched by UUID) are skipped,
     so re-running is safe.
  4. Old prod database is opened read-only (autocommit, no writes).
"""

import json as _json
import os
import sys
from datetime import datetime

import psycopg
from psycopg.rows import dict_row

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()

OLD_PROD_DEFAULT_URL = os.environ.get("OLD_PROD_DB_URL", "")

# Standard M2M tables (no sort_value column — direct copy by ID).
# Vocabulary IDs are IDENTICAL between old prod and dalia20 (verified), so rows
# can be copied directly without any ID remapping on the value column.
M2M_TABLE_MAP = {
    "disciplines": (
        "curation_form_resourcecontent_disciplines",
        "curation_resourcecontent_disciplines",
        "resourcecontent_id",
        "discipline_id",
    ),
    "languages": (
        "curation_form_resourcecontent_languages",
        "curation_resourcecontent_languages",
        "resourcecontent_id",
        "language_id",
    ),
    "learning_resource_types": (
        "curation_form_resourcecontent_learning_resource_types",
        "curation_resourcecontent_learning_resource_types",
        "resourcecontent_id",
        "learningresourcetype_id",
    ),
    "licenses": (
        "curation_form_resourcecontent_licenses",
        "curation_resourcecontent_licenses",
        "resourcecontent_id",
        "license_id",
    ),
    "media_types": (
        "curation_form_resourcecontent_media_types",
        "curation_resourcecontent_media_types",
        "resourcecontent_id",
        "mediatype_id",
    ),
    "file_formats": (
        "curation_form_resourcecontent_file_formats",
        "curation_resourcecontent_file_formats",
        "resourcecontent_id",
        "fileformat_id",
    ),
    "proficiency_levels": (
        "curation_form_resourcecontent_proficiency_levels",
        "curation_resourcecontent_proficiency_levels",
        "resourcecontent_id",
        "proficiencylevel_id",
    ),
    "target_groups": (
        "curation_form_resourcecontent_target_groups",
        "curation_resourcecontent_target_groups",
        "resourcecontent_id",
        "targetgroup_id",
    ),
}


class Command(BaseCommand):
    help = "Import all data from old production PostgreSQL into dalia20."

    def add_arguments(self, parser):
        parser.add_argument("--db-url", default=OLD_PROD_DEFAULT_URL, help="Old prod DB URL")
        parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
        parser.add_argument(
            "--no-backup", action="store_true", help="Skip backup (not recommended)"
        )
        parser.add_argument("--backup-dir", default="/tmp", help="Backup directory (default: /tmp)")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        db_url = options["db_url"]

        if not db_url:
            raise CommandError(
                "OLD_PROD_DB_URL env var is not set and --db-url was not provided. "
                "Set the environment variable or pass --db-url postgresql://<USER>:<PASS>@<HOST>:<PORT>/<DB>."
            )

        # ------------------------------------------------------------------ #
        # Step 1 — Backup current dalia20 data BEFORE any writes             #
        # ------------------------------------------------------------------ #
        backup_file = None
        if not dry_run:
            if options["no_backup"]:
                self.stdout.write(self.style.WARNING("Skipping backup (--no-backup)."))
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = os.path.join(options["backup_dir"], f"db_backup_{timestamp}.dump")
                self.stdout.write(f"Creating backup: {backup_file}")
                try:
                    import subprocess

                    env = {
                        "PGPASSWORD": os.environ.get("POSTGRES_PASSWORD") or "",
                        "PATH": os.environ.get("PATH", "/usr/bin:/usr/local/bin"),
                    }
                    result = subprocess.run(
                        [
                            "pg_dump",
                            "-h",
                            os.environ.get("POSTGRES_HOST", "db"),
                            "-p",
                            os.environ.get("POSTGRES_PORT", "5432"),
                            "-U",
                            os.environ.get("POSTGRES_USER", "dalia20"),
                            "-F",
                            "c",  # custom format: faster, smaller, selective restore
                            "-f",
                            backup_file,
                            os.environ.get("POSTGRES_DB", "dalia20"),
                        ],
                        env=env,
                        capture_output=True,
                        text=True,
                    )
                    if result.returncode != 0:
                        raise RuntimeError(result.stderr.strip())
                    size = os.path.getsize(backup_file)
                    if size < 100:
                        raise RuntimeError("Backup file is suspiciously small")
                    self.stdout.write(
                        self.style.SUCCESS(f"Backup saved ({size:,} bytes): {backup_file}")
                    )
                    self.stdout.write(
                        f"  Restore: pg_restore -h db -U dalia20 -d dalia20 -c {backup_file}"
                    )
                except Exception as e:
                    self.stderr.write(f"Backup failed: {e}")
                    self.stderr.write("Use --no-backup to skip (not recommended).")
                    sys.exit(1)
        else:
            self.stdout.write("(dry-run: skipping backup)")

        # ------------------------------------------------------------------ #
        # Step 2 — Fetch all data from old prod (read-only connection)       #
        # ------------------------------------------------------------------ #
        self.stdout.write(
            f"Connecting to old prod: {db_url.split('@')[1] if '@' in db_url else db_url}"
        )
        try:
            old_conn = psycopg.connect(db_url, row_factory=dict_row)
        except Exception as e:
            self.stderr.write(f"Cannot connect to old prod: {e}")
            sys.exit(1)
        old_conn.autocommit = True
        old_cur = old_conn.cursor()

        # Fetch ALL users (not just content-related ones)
        old_cur.execute("SELECT id, email, username, first_name, last_name FROM auth_user")
        old_users = old_cur.fetchall()
        old_users_by_id = {u["id"]: u for u in old_users}
        all_old_user_ids = [u["id"] for u in old_users] or [0]

        # Fetch social accounts
        old_cur.execute(
            "SELECT sa.provider, sa.uid, sa.extra_data, sa.last_login, sa.date_joined, sa.user_id "
            "FROM socialaccount_socialaccount sa WHERE sa.user_id = ANY(%s)",
            (all_old_user_ids,),
        )
        old_social_accounts = old_cur.fetchall()

        # Fetch RelationTypeCategory
        old_cur.execute(
            'SELECT id, uuid, created, modified, is_active, name, description, color, "order" '
            "FROM curation_form_relationtypecategory"
        )
        old_relation_type_categories = old_cur.fetchall()

        # Fetch RelationType (depends on category)
        old_cur.execute(
            'SELECT id, uuid, created, modified, is_active, code, label, description, "order", category_id '
            "FROM curation_form_relationtype"
        )
        old_relation_types = old_cur.fetchall()

        # Fetch Organizations
        old_cur.execute(
            "SELECT id, uuid, created, modified, is_active, name, ror_id, homepage, uri, parent_organization_id "
            "FROM curation_form_organization"
        )
        old_organizations = old_cur.fetchall()

        # Fetch Persons (user profiles — needed for preferences page)
        old_cur.execute(
            "SELECT id, uuid, created, modified, is_active, user_id, first_name, last_name, "
            "orcid, homepage, uri, privacy_level, email_notifications "
            "FROM curation_form_person"
        )
        old_persons = old_cur.fetchall()

        # Fetch ALL resources
        old_cur.execute(
            "SELECT r.id, r.uuid, r.title, r.owner_id, r.is_removed, r.created, r.modified "
            "FROM curation_form_resource r"
        )
        old_resources = old_cur.fetchall()

        # Fetch all content
        old_cur.execute("""
            SELECT rc.id, rc.uuid, rc.resource_id, rc.title, rc.main_url,
                   rc.publication_date, rc.description, rc.size_mb,
                   rc.created_by_id, rc.submitted_for_review, rc.submitted_at,
                   rc.submitted_by_id, rc.created, rc.modified
            FROM curation_form_resourcecontent rc
        """)
        old_contents = old_cur.fetchall()

        # Fetch standard M2M rows (no sort_value)
        old_m2m = {}
        for rel_name, (old_tbl, _, fk_col, val_col) in M2M_TABLE_MAP.items():
            old_cur.execute(f"SELECT {fk_col}, {val_col} FROM {old_tbl}")
            old_m2m[rel_name] = old_cur.fetchall()

        # Fetch sorted M2M (organizations and people have a sort_value column)
        old_cur.execute(
            "SELECT id, sort_value, resourcecontent_id, organization_id "
            "FROM curation_form_resourcecontent_organizations ORDER BY sort_value"
        )
        old_m2m_organizations = old_cur.fetchall()

        old_cur.execute(
            "SELECT id, sort_value, resourcecontent_id, person_id "
            "FROM curation_form_resourcecontent_people ORDER BY sort_value"
        )
        old_m2m_people = old_cur.fetchall()

        # Fetch ResourceRelatedItem
        old_cur.execute(
            'SELECT id, uuid, created, modified, "order", target_url, content_id, relation_type_id '
            "FROM curation_form_resourcerelateditem"
        )
        old_related_items = old_cur.fetchall()

        # Fetch ResourceCommunityRelation
        old_cur.execute(
            'SELECT id, uuid, created, modified, "order", community_id, content_id, relation_type_id '
            "FROM curation_form_resourcecommunityrelation"
        )
        old_community_relations = old_cur.fetchall()

        old_conn.close()

        # ------------------------------------------------------------------ #
        # Step 3 — Preview (dry-run) or execute inside ONE atomic transaction #
        # ------------------------------------------------------------------ #
        if dry_run:
            self._preview(
                old_users,
                old_social_accounts,
                old_relation_type_categories,
                old_relation_types,
                old_organizations,
                old_persons,
                old_resources,
                old_contents,
                old_related_items,
                old_community_relations,
                old_users_by_id,
                old_m2m_organizations,
                old_m2m_people,
            )
            self.stdout.write("Dry run complete.")
            return

        self.stdout.write("Starting atomic import — any error will roll back all changes.")
        try:
            with transaction.atomic():
                user_map = self._import_users(old_users)
                self._import_social_accounts(old_social_accounts, user_map)
                cat_map = self._import_relation_type_categories(old_relation_type_categories)
                rt_map = self._import_relation_types(old_relation_types, cat_map)
                org_map = self._import_organizations(old_organizations)
                person_map = self._import_persons(old_persons, user_map)
                resource_map, content_map = self._import_resources_and_contents(
                    old_resources, old_contents, user_map
                )
                self._import_m2m(old_m2m, content_map)
                self._import_sorted_m2m(
                    old_m2m_organizations,
                    content_map,
                    org_map,
                    "curation_resourcecontent_organizations",
                    "organization_id",
                )
                self._import_sorted_m2m(
                    old_m2m_people,
                    content_map,
                    person_map,
                    "curation_resourcecontent_people",
                    "person_id",
                )
                self._import_resource_related_items(old_related_items, content_map, rt_map)
                self._import_resource_community_relations(
                    old_community_relations, content_map, rt_map
                )
        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f"\nIMPORT FAILED — all changes rolled back.\nError: {e}")
            )
            if backup_file:
                self.stderr.write(f"Your data is unchanged. Backup at: {backup_file}")
            raise

        self.stdout.write(self.style.SUCCESS("Import complete! All changes committed."))
        if backup_file:
            self.stdout.write(f"Backup retained at: {backup_file}")

    # ------------------------------------------------------------------ #
    # Helpers                                                             #
    # ------------------------------------------------------------------ #

    def _preview(
        self,
        old_users,
        old_social_accounts,
        old_cats,
        old_types,
        old_organizations,
        old_persons,
        old_resources,
        old_contents,
        old_related_items,
        old_community_relations,
        old_users_by_id,
        old_m2m_organizations,
        old_m2m_people,
    ):
        self.stdout.write(f"--- USERS ({len(old_users)}) ---")
        for u in old_users:
            existing = None
            if u["email"]:
                existing = User.objects.filter(email=u["email"]).first()
            if not existing:
                existing = User.objects.filter(username=u["username"]).first()
            status = (
                f"matched '{u['username']}' -> id {existing.id}"
                if existing
                else f"would create '{u['username']}' ({u['email']})"
            )
            self.stdout.write(f"  {status}")

        self.stdout.write(f"--- SOCIAL ACCOUNTS ({len(old_social_accounts)}) ---")
        for sa in old_social_accounts:
            u = old_users_by_id.get(sa["user_id"], {})
            self.stdout.write(
                f"  {sa['provider']} uid={sa['uid'][:16]}... for '{u.get('username', '?')}'"
            )

        self.stdout.write(f"--- RELATION TYPE CATEGORIES ({len(old_cats)}) ---")
        for c in old_cats:
            self.stdout.write(f"  {c['name']}")

        self.stdout.write(f"--- RELATION TYPES ({len(old_types)}) ---")
        for t in old_types:
            self.stdout.write(f"  {t['code']} — {t['label']}")

        self.stdout.write(f"--- ORGANIZATIONS ({len(old_organizations)}) ---")
        for o in old_organizations:
            self.stdout.write(f"  {o['name']}")

        self.stdout.write(f"--- PERSONS ({len(old_persons)}) ---")
        for p in old_persons:
            u = old_users_by_id.get(p["user_id"], {})
            self.stdout.write(
                f"  {p['first_name']} {p['last_name']} (user: {u.get('username', '?')})"
            )

        self.stdout.write(f"--- RESOURCES ({len(old_resources)}) ---")
        for r in old_resources:
            self.stdout.write(f"  {r['uuid']} — {r['title'] or '(no title)'}")

        self.stdout.write(f"--- CONTENT ({len(old_contents)}) ---")
        for rc in old_contents:
            self.stdout.write(f"  {rc['uuid']} — {rc['title']}")

        self.stdout.write(f"--- RESOURCE RELATED ITEMS ({len(old_related_items)}) ---")
        for item in old_related_items:
            self.stdout.write(f"  {item['uuid']} — {item['target_url'][:60]}")

        self.stdout.write(f"--- RESOURCE COMMUNITY RELATIONS ({len(old_community_relations)}) ---")
        for rel in old_community_relations:
            self.stdout.write(f"  content={rel['content_id']} community={rel['community_id']}")

        self.stdout.write(f"--- M2M ORGANIZATIONS ({len(old_m2m_organizations)}) ---")
        self.stdout.write(f"  {len(old_m2m_organizations)} rows")

        self.stdout.write(f"--- M2M PEOPLE ({len(old_m2m_people)}) ---")
        self.stdout.write(f"  {len(old_m2m_people)} rows")

    def _import_users(self, old_users):
        user_map = {}
        default_admin_id = (
            User.objects.filter(is_superuser=True).values_list("id", flat=True).first()
        )
        for u in old_users:
            new_user = self._get_or_create_user(u)
            uid = new_user.id if new_user else default_admin_id
            user_map[u["id"]] = uid
            label = f"id {new_user.id}" if new_user else f"fallback admin id {default_admin_id}"
            self.stdout.write(f"  User '{u['username']}' -> {label}")
        return user_map

    def _get_or_create_user(self, old_user):
        # Matching priority: email first (most reliable), then username.
        # Users that cannot be matched are created as inactive — they become
        # active automatically the first time they log in via OIDC.
        # dalia20 User.email is null=False, unique=True — blank emails from old
        # prod would collide. Use a per-username placeholder so each row is unique.
        email = old_user["email"] or None
        if email:
            existing = User.objects.filter(email=email).first()
            if existing:
                return existing
        existing = User.objects.filter(username=old_user["username"]).first()
        if existing:
            return existing
        create_email = email if email else f"{old_user['username']}@imported.no-email.local"
        return User.objects.create_user(
            username=old_user["username"],
            email=create_email,
            first_name=old_user["first_name"] or "",
            last_name=old_user["last_name"] or "",
            is_active=False,
            password=None,
        )

    def _import_social_accounts(self, old_social_accounts, user_map):
        # Insert OIDC SocialAccount records so that when a user logs in via
        # IAM4NFDI, allauth matches them by (provider, uid=sub) and links to
        # the already-imported User — preventing duplicate user creation.
        # ON CONFLICT DO NOTHING makes this idempotent on re-runs.
        from django.db import connection as django_conn

        with django_conn.cursor() as cur:
            for sa in old_social_accounts:
                new_user_id = user_map.get(sa["user_id"])
                if not new_user_id:
                    continue
                extra = (
                    sa["extra_data"]
                    if isinstance(sa["extra_data"], str)
                    else _json.dumps(sa["extra_data"])
                )
                cur.execute(
                    "INSERT INTO socialaccount_socialaccount "
                    "    (provider, uid, extra_data, last_login, date_joined, user_id) "
                    "VALUES (%s, %s, %s, %s, %s, %s) "
                    "ON CONFLICT (provider, uid) DO NOTHING",
                    [
                        sa["provider"],
                        sa["uid"],
                        extra,
                        sa["last_login"],
                        sa["date_joined"],
                        new_user_id,
                    ],
                )
                self.stdout.write(
                    f"  SocialAccount: {sa['provider']} uid={sa['uid'][:16]}... -> user_id {new_user_id}"
                )

    def _import_relation_type_categories(self, old_cats):
        from curation.models import RelationTypeCategory

        cat_map = {}
        for c in old_cats:
            existing = RelationTypeCategory.objects.filter(uuid=c["uuid"]).first()
            if existing:
                cat_map[c["id"]] = existing.id
                self.stdout.write(f"  RelationTypeCategory '{c['name']}' already exists, skipping")
                continue
            new_c = RelationTypeCategory.objects.create(
                uuid=c["uuid"],
                name=c["name"],
                description=c["description"] or "",
                color=c["color"] or "",
                order=c["order"],
                is_active=c["is_active"],
            )
            RelationTypeCategory.objects.filter(pk=new_c.pk).update(
                created=c["created"], modified=c["modified"]
            )
            cat_map[c["id"]] = new_c.id
            self.stdout.write(f"  RelationTypeCategory '{c['name']}' -> id {new_c.id}")
        return cat_map

    def _import_relation_types(self, old_types, cat_map):
        from curation.models import RelationType

        rt_map = {}
        for t in old_types:
            existing = RelationType.objects.filter(uuid=t["uuid"]).first()
            if existing:
                rt_map[t["id"]] = existing.id
                continue
            new_t = RelationType.objects.create(
                uuid=t["uuid"],
                code=t["code"],
                label=t["label"],
                description=t["description"] or "",
                order=t["order"],
                is_active=t["is_active"],
                category_id=cat_map.get(t["category_id"]),
            )
            RelationType.objects.filter(pk=new_t.pk).update(
                created=t["created"], modified=t["modified"]
            )
            rt_map[t["id"]] = new_t.id
        self.stdout.write(f"  RelationTypes: {len(old_types)} processed")
        return rt_map

    def _import_organizations(self, old_orgs):
        from curation.models import Organization

        org_map = {}
        # First pass: create all without parent links
        for o in old_orgs:
            existing = Organization.objects.filter(uuid=o["uuid"]).first()
            if existing:
                org_map[o["id"]] = existing.id
                self.stdout.write(f"  Organization '{o['name']}' already exists, skipping")
                continue
            new_o = Organization.objects.create(
                uuid=o["uuid"],
                name=o["name"],
                ror_id=o["ror_id"] or "",
                homepage=o["homepage"] or "",
                uri=o["uri"] or "",
                is_active=o["is_active"],
            )
            Organization.objects.filter(pk=new_o.pk).update(
                created=o["created"], modified=o["modified"]
            )
            org_map[o["id"]] = new_o.id
            self.stdout.write(f"  Organization '{o['name']}' -> id {new_o.id}")
        # Second pass: set parent links (handles self-referential FK)
        for o in old_orgs:
            if o["parent_organization_id"] and o["parent_organization_id"] in org_map:
                new_org_id = org_map[o["id"]]
                new_parent_id = org_map[o["parent_organization_id"]]
                Organization.objects.filter(pk=new_org_id).update(
                    parent_organization_id=new_parent_id
                )
        return org_map

    def _import_persons(self, old_persons, user_map):
        from curation.models import Person

        person_map = {}
        for p in old_persons:
            existing = Person.objects.filter(uuid=p["uuid"]).first()
            if existing:
                person_map[p["id"]] = existing.id
                self.stdout.write(
                    f"  Person '{p['first_name']} {p['last_name']}' already exists, skipping"
                )
                continue
            # user_id may be None for external contributors (no login account)
            new_user_id = user_map.get(p["user_id"]) if p["user_id"] is not None else None
            # Avoid duplicate person for same user (only when user is present)
            if new_user_id is not None:
                existing_for_user = Person.objects.filter(user_id=new_user_id).first()
                if existing_for_user:
                    person_map[p["id"]] = existing_for_user.id
                    self.stdout.write(
                        f"  Person for user {new_user_id} already exists (id {existing_for_user.id}), skipping"
                    )
                    continue
            new_p = Person.objects.create(
                uuid=p["uuid"],
                user_id=new_user_id,
                first_name=p["first_name"] or "",
                last_name=p["last_name"] or "",
                orcid=p["orcid"] or "",
                homepage=p["homepage"] or "",
                uri=p["uri"] or "",
                privacy_level=p["privacy_level"],
                email_notifications=p["email_notifications"],
                is_active=p["is_active"],
            )
            Person.objects.filter(pk=new_p.pk).update(created=p["created"], modified=p["modified"])
            person_map[p["id"]] = new_p.id
            self.stdout.write(f"  Person '{p['first_name']} {p['last_name']}' -> id {new_p.id}")
        return person_map

    def _import_resources_and_contents(self, old_resources, old_contents, user_map):
        # Resource is the grouper (one per logical resource); ResourceContent
        # holds the versioned metadata. Old prod had django-cms-versioning states
        # (DRAFT/PUBLISHED); dalia20 uses is_published bool on Resource.
        # All old prod records were DRAFT, so is_published=False here.
        # UUIDs are preserved to keep external references intact.
        # Timestamps are restored via a secondary .update() because .create()
        # ignores auto_now_add fields.
        from curation.models import Resource, ResourceContent

        default_admin_id = (
            User.objects.filter(is_superuser=True).values_list("id", flat=True).first()
        )

        resource_map = {}
        for r in old_resources:
            owner_id = user_map.get(r["owner_id"], default_admin_id)
            existing = Resource.objects.filter(uuid=r["uuid"]).first()
            if existing:
                resource_map[r["id"]] = existing.id
                self.stdout.write(f"  Resource '{r['title']}' already exists, skipping")
                continue
            new_r = Resource.objects.create(
                uuid=r["uuid"],
                title=r["title"] or "",
                owner_id=owner_id,
                is_removed=r["is_removed"],
                is_published=False,
                version=1,
            )
            Resource.objects.filter(pk=new_r.pk).update(
                created=r["created"], modified=r["modified"]
            )
            resource_map[r["id"]] = new_r.id
            self.stdout.write(f"  Resource '{r['title']}' -> id {new_r.id}")

        content_map = {}
        for rc in old_contents:
            new_resource_id = resource_map.get(rc["resource_id"])
            if not new_resource_id:
                self.stdout.write(f"  SKIP content '{rc['title']}': no resource mapping")
                continue
            created_by_id = user_map.get(rc["created_by_id"], default_admin_id)
            submitted_by_id = user_map.get(rc["submitted_by_id"]) if rc["submitted_by_id"] else None
            existing = ResourceContent.objects.filter(uuid=rc["uuid"]).first()
            if existing:
                content_map[rc["id"]] = existing.id
                self.stdout.write(f"  Content '{rc['title']}' already exists, skipping")
                continue
            new_rc = ResourceContent.objects.create(
                uuid=rc["uuid"],
                resource_id=new_resource_id,
                title=rc["title"],
                main_url=rc["main_url"],
                publication_date=rc["publication_date"],
                description=rc["description"] or "",
                size_mb=rc["size_mb"],
                created_by_id=created_by_id,
                submitted_for_review=rc["submitted_for_review"],
                submitted_at=rc["submitted_at"],
                submitted_by_id=submitted_by_id,
            )
            ResourceContent.objects.filter(pk=new_rc.pk).update(
                created=rc["created"], modified=rc["modified"]
            )
            content_map[rc["id"]] = new_rc.id
            self.stdout.write(f"  Content '{rc['title']}' -> id {new_rc.id}")

        return resource_map, content_map

    def _import_m2m(self, old_m2m, content_map):
        # Copy standard M2M junction rows using raw SQL.
        # content_map translates old ResourceContent IDs to new ones.
        # Vocabulary value IDs need no remapping (identical sequences in both DBs).
        from django.db import connection as django_conn

        with django_conn.cursor() as cur:
            for rel_name, (_, new_tbl, fk_col, val_col) in M2M_TABLE_MAP.items():
                count = 0
                for row in old_m2m[rel_name]:
                    new_content_id = content_map.get(row[fk_col])
                    if not new_content_id:
                        continue
                    cur.execute(
                        f"INSERT INTO {new_tbl} (resourcecontent_id, {val_col}) "
                        f"VALUES (%s, %s) ON CONFLICT DO NOTHING",
                        [new_content_id, row[val_col]],
                    )
                    count += 1
                self.stdout.write(f"  M2M {rel_name}: {count} rows")

    def _import_sorted_m2m(self, old_rows, content_map, value_map, new_tbl, val_col):
        # Copy sorted M2M rows (organizations, people) that have a sort_value column.
        # value_map translates old IDs to new ones (e.g. old org_id → new org_id).
        from django.db import connection as django_conn

        count = 0
        skip = 0
        with django_conn.cursor() as cur:
            for row in old_rows:
                new_content_id = content_map.get(row["resourcecontent_id"])
                old_value_id = row[val_col]
                new_value_id = value_map.get(old_value_id) if value_map else old_value_id
                if not new_content_id or not new_value_id:
                    skip += 1
                    continue
                cur.execute(
                    f"INSERT INTO {new_tbl} (resourcecontent_id, {val_col}, sort_value) "
                    f"VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                    [new_content_id, new_value_id, row["sort_value"]],
                )
                count += 1
        self.stdout.write(f"  {new_tbl}: {count} rows ({skip} skipped — no content/value mapping)")

    def _import_resource_related_items(self, old_items, content_map, rt_map):
        from curation.models import ResourceRelatedItem

        count = 0
        skip = 0
        for item in old_items:
            new_content_id = content_map.get(item["content_id"])
            if not new_content_id:
                skip += 1
                continue
            existing = ResourceRelatedItem.objects.filter(uuid=item["uuid"]).first()
            if existing:
                continue
            new_item = ResourceRelatedItem.objects.create(
                uuid=item["uuid"],
                content_id=new_content_id,
                relation_type_id=rt_map.get(item["relation_type_id"]),
                target_url=item["target_url"],
                order=item["order"],
            )
            ResourceRelatedItem.objects.filter(pk=new_item.pk).update(
                created=item["created"], modified=item["modified"]
            )
            count += 1
        self.stdout.write(f"  ResourceRelatedItems: {count} imported, {skip} skipped")

    def _import_resource_community_relations(self, old_relations, content_map, rt_map):
        from curation.models import ResourceCommunityRelation, Community

        count = 0
        skip = 0
        for rel in old_relations:
            new_content_id = content_map.get(rel["content_id"])
            if not new_content_id:
                skip += 1
                continue
            # Community IDs are identical between old prod and dalia20 (same UUIDs, same IDs)
            community = Community.objects.filter(id=rel["community_id"]).first()
            if not community:
                self.stdout.write(
                    f"  SKIP ResourceCommunityRelation: community {rel['community_id']} not found"
                )
                skip += 1
                continue
            existing = ResourceCommunityRelation.objects.filter(uuid=rel["uuid"]).first()
            if existing:
                continue
            new_rel = ResourceCommunityRelation.objects.create(
                uuid=rel["uuid"],
                content_id=new_content_id,
                community_id=community.id,
                relation_type_id=rt_map.get(rel["relation_type_id"]),
                order=rel["order"],
            )
            ResourceCommunityRelation.objects.filter(pk=new_rel.pk).update(
                created=rel["created"], modified=rel["modified"]
            )
            count += 1
        self.stdout.write(f"  ResourceCommunityRelations: {count} imported, {skip} skipped")

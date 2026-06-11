import json
from django.contrib import admin, messages
from django.db.models import Q, Count
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.template.response import TemplateResponse
from django.shortcuts import get_object_or_404

from core.admin import BaseModelAdmin
from ..models import EntityMapping, SyncLog
from ..services.import_candidate_service import ImportCandidateService
from ..services.fuseki_query_service import FusekiQueryService
from ..services.entity_creation_service import EntityCreationService


@admin.register(EntityMapping)
class EntityMappingAdmin(BaseModelAdmin):
    """
    Enhanced admin interface for EntityMapping with import candidate management.
    """

    change_list_template = "admin/entity_mapping/change_list.html"

    list_display = [
        "id",
        "entity_type_display",
        "sync_status_display",
        "postgresql_uuid_display",
        "fuseki_uuid_display",
        "fuseki_uri_display",
        "import_candidate_display",
        "sync_age_display",
        "created",
        "actions_display",
    ]

    list_filter = [
        "entity_type",
        "sync_status",
        "import_candidate",
        "import_approved",
        "sync_direction",
        "created",
        "last_sync_at",
    ]

    search_fields = [
        "postgresql_uuid",
        "fuseki_uuid",
        "fuseki_uri",
        "sync_notes",
        "fuseki_metadata",
    ]

    readonly_fields = [
        "created",
        "modified",
        "sync_age_days",
        "is_bidirectional",
        "needs_postgresql_creation",
    ]

    fieldsets = (
        (
            "Entity Identification",
            {"fields": ("entity_type", "postgresql_uuid", "fuseki_uuid", "fuseki_uri")},
        ),
        (
            "Synchronization",
            {"fields": ("sync_status", "sync_direction", "last_sync_at", "sync_notes")},
        ),
        (
            "Import Management",
            {"fields": ("import_candidate", "import_approved"), "classes": ("collapse",)},
        ),
        ("Metadata", {"fields": ("fuseki_metadata", "created_by"), "classes": ("collapse",)}),
        (
            "Status Information",
            {
                "fields": (
                    "created",
                    "modified",
                    "sync_age_days",
                    "is_bidirectional",
                    "needs_postgresql_creation",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    actions = [
        "mark_as_synced",
        "mark_for_resync",
        "approve_selected_imports",
        "approve_all_import_candidates",
        "reject_selected_imports",
        "cleanup_import_candidates",
        "preview_entity_transformation",
        "validate_entity_data",
        "create_postgresql_entities",
    ]

    def get_urls(self):
        """Add custom admin URLs."""
        urls = super().get_urls()
        custom_urls = [
            path(
                "import-candidates/",
                self.admin_site.admin_view(self.import_candidates_view),
                name="entity_mapping_import_candidates",
            ),
            path(
                "discover-candidates/",
                self.admin_site.admin_view(self.discover_candidates_view),
                name="entity_mapping_discover_candidates",
            ),
            path(
                "approve-import/<int:mapping_id>/",
                self.admin_site.admin_view(self.approve_import_view),
                name="entity_mapping_approve_import",
            ),
            path(
                "reject-import/<int:mapping_id>/",
                self.admin_site.admin_view(self.reject_import_view),
                name="entity_mapping_reject_import",
            ),
            path(
                "sync-summary/",
                self.admin_site.admin_view(self.sync_summary_view),
                name="entity_mapping_sync_summary",
            ),
            path(
                "preview-entity/<int:mapping_id>/",
                self.admin_site.admin_view(self.preview_entity_view),
                name="entity_mapping_preview_entity",
            ),
            path(
                "create-entity/<int:mapping_id>/",
                self.admin_site.admin_view(self.create_entity_view),
                name="entity_mapping_create_entity",
            ),
        ]
        return custom_urls + urls

    # Display methods
    def entity_type_display(self, obj):
        """Display entity type with color coding."""
        colors = {
            "license": "#28a745",
            "discipline": "#007bff",
            "community": "#17a2b8",
            "person": "#fd7e14",
            "organization": "#6f42c1",
        }
        color = colors.get(obj.entity_type, "#6c757d")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_entity_type_display(),
        )

    entity_type_display.short_description = "Type"

    def sync_status_display(self, obj):
        """Display sync status with badge styling."""
        status_styles = {
            "pending": "background: #ffc107; color: #000;",
            "synced": "background: #28a745; color: #fff;",
            "failed": "background: #dc3545; color: #fff;",
            "outdated": "background: #fd7e14; color: #fff;",
            "conflict": "background: #6f42c1; color: #fff;",
        }
        style = status_styles.get(obj.sync_status, "background: #6c757d; color: #fff;")
        return format_html(
            '<span style="padding: 3px 8px; border-radius: 3px; font-size: 11px; {}">{}</span>',
            style,
            obj.get_sync_status_display(),
        )

    sync_status_display.short_description = "Status"

    def postgresql_uuid_display(self, obj):
        """Display PostgreSQL UUID with copy functionality."""
        if obj.postgresql_uuid:
            return format_html(
                '<code style="font-size: 11px;" title="Click to copy">{}</code>',
                str(obj.postgresql_uuid)[:8] + "...",
            )
        return mark_safe('<em style="color: #6c757d;">Not mapped</em>')

    postgresql_uuid_display.short_description = "PostgreSQL UUID"

    def fuseki_uuid_display(self, obj):
        """Display Fuseki UUID with copy functionality."""
        if obj.fuseki_uuid:
            return format_html(
                '<code style="font-size: 11px;" title="Click to copy">{}</code>',
                str(obj.fuseki_uuid)[:8] + "...",
            )
        return mark_safe('<em style="color: #6c757d;">None</em>')

    fuseki_uuid_display.short_description = "Fuseki UUID"

    def fuseki_uri_display(self, obj):
        """Display Fuseki URI as clickable link."""
        if obj.fuseki_uri:
            # Extract readable part from URI
            if "#" in obj.fuseki_uri:
                display_text = obj.fuseki_uri.split("#")[-1]
            elif "/" in obj.fuseki_uri:
                display_text = obj.fuseki_uri.split("/")[-1]
            else:
                display_text = obj.fuseki_uri

            return format_html(
                '<a href="{}" target="_blank" title="{}" style="font-size: 11px;">{}</a>',
                obj.fuseki_uri,
                obj.fuseki_uri,
                display_text[:20] + ("..." if len(display_text) > 20 else ""),
            )
        return mark_safe('<em style="color: #6c757d;">None</em>')

    fuseki_uri_display.short_description = "Fuseki URI"

    def import_candidate_display(self, obj):
        """Display import candidate status."""
        if obj.import_candidate:
            if obj.import_approved:
                return mark_safe('<span style="color: #28a745;font-weight:500;">✓ Approved</span>')
            else:
                return mark_safe('<span style="color: #d97706;font-weight:500;">⏳ Pending</span>')
        return "-"

    import_candidate_display.short_description = "Import"

    def sync_age_display(self, obj):
        """Display sync age with warning for old syncs."""
        age = obj.sync_age_days
        if age is None:
            return mark_safe('<em style="color: #6c757d;">Never</em>')
        elif age > 30:
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;">{} days</span>', age
            )
        elif age > 7:
            return format_html('<span style="color: #fd7e14;">{} days</span>', age)
        else:
            return format_html("{} days", age)

    sync_age_display.short_description = "Last Sync"

    def actions_display(self, obj):
        """Display action buttons for each mapping."""
        actions = []

        if obj.import_candidate and not obj.import_approved:
            approve_url = reverse("admin:entity_mapping_approve_import", args=[obj.id])
            reject_url = reverse("admin:entity_mapping_reject_import", args=[obj.id])
            actions.extend(
                [
                    f'<a href="{approve_url}" style="color: #28a745; margin-right: 10px;" title="Approve Import">✓</a>',
                    f'<a href="{reject_url}" style="color: #dc3545;" title="Reject Import">✗</a>',
                ]
            )

        # Add preview button for approved candidates
        if obj.import_approved and not obj.postgresql_uuid:
            preview_url = reverse("admin:entity_mapping_preview_entity", args=[obj.id])
            actions.append(
                f'<a href="{preview_url}" style="color: #007bff; margin-left: 10px;" title="Preview Entity">🔍</a>'
            )

        if not actions:
            actions.append('<span style="color: #6c757d;">-</span>')

        return mark_safe(" ".join(actions))

    actions_display.short_description = "Actions"

    # Custom views
    def import_candidates_view(self, request):
        """View for managing import candidates."""
        from django.core.paginator import Paginator

        service = ImportCandidateService()
        summary = service.get_import_candidates_summary()

        # Get all candidates with pagination
        candidates_list = (
            EntityMapping.objects.filter(import_candidate=True)
            .select_related("created_by")
            .order_by("-created")
        )

        # Pagination
        paginator = Paginator(candidates_list, 25)  # Show 25 candidates per page
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        # Build context with admin context for Jazzmin sidebar
        context = dict(self.admin_site.each_context(request))
        context.update(
            {
                "title": "Import Candidates Management",
                "summary": summary,
                "recent_candidates": page_obj,
                "page_obj": page_obj,
                "is_paginated": page_obj.has_other_pages(),
                "opts": self.model._meta,
                "has_view_permission": self.has_view_permission(request),
            }
        )

        return TemplateResponse(request, "admin/entity_mapping/import_candidates.html", context)

    def discover_candidates_view(self, request):
        """View for discovering new import candidates."""
        if request.method == "POST":
            entity_type = request.POST.get("entity_type")
            limit = int(request.POST.get("limit", 1000))

            service = ImportCandidateService()
            results = service.discover_import_candidates(
                entity_type=entity_type if entity_type != "all" else None,
                user=request.user,
                limit=limit,
            )

            total_found = sum(results.values())
            messages.success(
                request, f"Discovery complete! Found {total_found} new import candidates."
            )

            return HttpResponseRedirect(reverse("admin:entity_mapping_import_candidates"))

        # GET request - show discovery form
        entity_types = [
            ("all", "All Entity Types"),
            *[(k, v) for k, v in EntityMapping.ENTITY_TYPE_CHOICES],
        ]

        # Build context with admin context for Jazzmin sidebar
        context = dict(self.admin_site.each_context(request))
        context.update(
            {
                "title": "Discover Import Candidates",
                "entity_types": entity_types,
                "opts": self.model._meta,
                "has_add_permission": self.has_add_permission(request),
            }
        )

        return TemplateResponse(request, "admin/entity_mapping/discover_candidates.html", context)

    def approve_import_view(self, request, mapping_id):
        """Approve a specific import candidate."""
        service = ImportCandidateService()
        success = service.approve_import_candidate(mapping_id, request.user)

        if success:
            messages.success(request, "Import candidate approved successfully.")
        else:
            messages.error(request, "Failed to approve import candidate.")

        return HttpResponseRedirect(reverse("admin:entity_mapping_entitymapping_changelist"))

    def reject_import_view(self, request, mapping_id):
        """Reject a specific import candidate."""
        reason = request.GET.get("reason", "Rejected via admin interface")
        service = ImportCandidateService()
        success = service.reject_import_candidate(mapping_id, request.user, reason)

        if success:
            messages.success(request, "Import candidate rejected.")
        else:
            messages.error(request, "Failed to reject import candidate.")

        return HttpResponseRedirect(reverse("admin:entity_mapping_entitymapping_changelist"))

    def sync_summary_view(self, request):
        """View showing synchronization summary and statistics."""
        # Calculate summary statistics
        stats = {}
        total_mappings = 0
        total_synced = 0
        total_pending = 0
        total_failed = 0
        total_import_candidates = 0

        for entity_type, _ in EntityMapping.ENTITY_TYPE_CHOICES:
            # Count actual mappings (entities with PostgreSQL UUID - real mappings)
            mappings = EntityMapping.objects.filter(
                entity_type=entity_type, postgresql_uuid__isnull=False
            )
            # Count import candidates (entities waiting for PostgreSQL creation)
            import_candidates = EntityMapping.objects.filter(
                entity_type=entity_type, import_candidate=True
            )

            entity_stats = {
                "total": mappings.count(),
                "synced": mappings.filter(sync_status="synced").count(),
                "pending": mappings.filter(sync_status="pending").count(),
                "failed": mappings.filter(sync_status="failed").count(),
                "import_candidates": import_candidates.count(),
            }

            stats[entity_type] = entity_stats

            # Accumulate totals
            total_mappings += entity_stats["total"]
            total_synced += entity_stats["synced"]
            total_pending += entity_stats["pending"]
            total_failed += entity_stats["failed"]
            total_import_candidates += entity_stats["import_candidates"]

        # Build context with admin context for Jazzmin sidebar
        context = dict(self.admin_site.each_context(request))
        context.update(
            {
                "title": "Synchronization Summary",
                "stats": stats,
                "total_mappings": total_mappings,
                "total_synced": total_synced,
                "total_pending": total_pending,
                "total_failed": total_failed,
                "total_import_candidates": total_import_candidates,
                "opts": self.model._meta,
                "has_view_permission": self.has_view_permission(request),
            }
        )

        return TemplateResponse(request, "admin/entity_mapping/sync_summary.html", context)

    # Admin actions
    def mark_as_synced(self, request, queryset):
        """Mark selected mappings as synced."""
        updated = queryset.update(sync_status="synced")
        self.message_user(
            request, f"Successfully marked {updated} mappings as synced.", messages.SUCCESS
        )

    mark_as_synced.short_description = "Mark selected as synced"

    def mark_for_resync(self, request, queryset):
        """Mark selected mappings for resynchronization."""
        updated = queryset.update(sync_status="pending")
        self.message_user(
            request, f"Successfully marked {updated} mappings for resync.", messages.SUCCESS
        )

    mark_for_resync.short_description = "Mark selected for resync"

    def approve_selected_imports(self, request, queryset):
        """Approve selected import candidates."""
        service = ImportCandidateService()
        approved = 0

        for mapping in queryset.filter(import_candidate=True, import_approved=False):
            if service.approve_import_candidate(mapping.id, request.user):
                approved += 1

        self.message_user(
            request, f"Successfully approved {approved} import candidates.", messages.SUCCESS
        )

    approve_selected_imports.short_description = "Approve selected import candidates"

    def reject_selected_imports(self, request, queryset):
        """Reject selected import candidates."""
        service = ImportCandidateService()
        rejected = 0

        for mapping in queryset.filter(import_candidate=True):
            if service.reject_import_candidate(mapping.id, request.user, "Bulk rejection"):
                rejected += 1

        self.message_user(
            request, f"Successfully rejected {rejected} import candidates.", messages.SUCCESS
        )

    reject_selected_imports.short_description = "Reject selected import candidates"

    def preview_entity_transformation(self, request, queryset):
        """Preview entity transformation for selected mappings."""
        if queryset.count() > 10:
            self.message_user(
                request, "Please select 10 or fewer items for preview.", messages.WARNING
            )
            return

        service = EntityCreationService(request.user)
        previews = []

        for mapping in queryset:
            preview = service.preview_transformation(mapping)
            previews.append(preview)

        # Store previews in session for the preview page
        request.session["entity_previews"] = previews

        # Redirect to a preview page
        return HttpResponseRedirect(
            reverse("admin:entity_mapping_entitymapping_changelist") + "?preview=1"
        )

    preview_entity_transformation.short_description = "Preview entity transformation"

    def validate_entity_data(self, request, queryset):
        """Validate entity data for selected mappings."""
        service = EntityCreationService(request.user)
        valid_count = 0
        invalid_count = 0

        for mapping in queryset:
            result = service.validate_before_creation(mapping)
            if result.is_valid:
                valid_count += 1
            else:
                invalid_count += 1
                # Show first error for context
                error_msg = result.errors[0] if result.errors else "Unknown error"
                self.message_user(
                    request,
                    f"Validation failed for {mapping.entity_type} #{mapping.id}: {error_msg}",
                    messages.ERROR,
                )

        if valid_count > 0:
            self.message_user(
                request,
                f"✅ {valid_count} entity/entities validated successfully.",
                messages.SUCCESS,
            )

        if invalid_count > 0:
            self.message_user(
                request,
                f"❌ {invalid_count} entity/entities have validation errors.",
                messages.ERROR,
            )

    validate_entity_data.short_description = "Validate entity data"

    def create_postgresql_entities(self, request, queryset):
        """Create PostgreSQL entities from selected approved import candidates."""
        # Filter for approved candidates without PostgreSQL UUID
        candidates = queryset.filter(import_approved=True, postgresql_uuid__isnull=True)

        if candidates.count() == 0:
            self.message_user(
                request,
                "No approved import candidates selected (or entities already created).",
                messages.WARNING,
            )
            return

        service = EntityCreationService(request.user)
        results, stats = service.bulk_create_entities(list(candidates))

        # Show results
        if stats["success"] > 0:
            self.message_user(
                request,
                f"✅ Successfully created {stats['success']} PostgreSQL entities.",
                messages.SUCCESS,
            )

        if stats["failed"] > 0:
            self.message_user(
                request,
                f"❌ Failed to create {stats['failed']} entities. Check sync logs for details.",
                messages.ERROR,
            )

            # Show some error details
            for result in results:
                if not result.success and result.errors:
                    error_msg = result.errors[0] if result.errors else result.message
                    self.message_user(
                        request,
                        f"Error for mapping #{result.entity_mapping_id}: {error_msg}",
                        messages.ERROR,
                    )

    create_postgresql_entities.short_description = (
        "Create PostgreSQL entities from approved candidates"
    )

    def approve_all_import_candidates(self, request, queryset):
        """
        Approve ALL pending import candidates (not limited to selection).
        Shows confirmation page before executing.
        """
        # Get all pending candidates (not just the selected queryset)
        all_pending = EntityMapping.objects.filter(import_candidate=True, import_approved=False)

        total_count = all_pending.count()

        if total_count == 0:
            self.message_user(
                request, "No pending import candidates found to approve.", messages.WARNING
            )
            return HttpResponseRedirect(reverse("admin:entity_mapping_entitymapping_changelist"))

        # Confirmation check via POST parameter
        if request.POST.get("confirm_approve_all"):
            service = ImportCandidateService()
            approved = 0

            for mapping in all_pending:
                if service.approve_import_candidate(mapping.id, request.user):
                    approved += 1

            self.message_user(
                request, f"✅ Successfully approved {approved} import candidates.", messages.SUCCESS
            )
            return HttpResponseRedirect(reverse("admin:entity_mapping_entitymapping_changelist"))

        # Show confirmation page
        from django.template.response import TemplateResponse

        # Group by entity type for display
        by_type = {}
        for mapping in all_pending:
            entity_type = mapping.get_entity_type_display()
            by_type[entity_type] = by_type.get(entity_type, 0) + 1

        context = dict(
            self.admin_site.each_context(request),
            title="Confirm Bulk Approval",
            total_count=total_count,
            by_type=by_type,
            action="approve_all_import_candidates",
            opts=self.model._meta,
        )

        return TemplateResponse(request, "admin/entity_mapping/confirm_bulk_action.html", context)

    approve_all_import_candidates.short_description = "⚡ Approve ALL pending import candidates"

    def cleanup_import_candidates(self, request, queryset):
        """
        Delete ALL non-approved import candidates (pending and rejected).
        This is a "start from scratch" operation.
        Shows confirmation page before executing.
        """
        # Get all non-approved candidates
        to_delete = EntityMapping.objects.filter(import_candidate=True, import_approved=False)

        total_count = to_delete.count()

        if total_count == 0:
            self.message_user(request, "No import candidates found to clean up.", messages.WARNING)
            return HttpResponseRedirect(reverse("admin:entity_mapping_entitymapping_changelist"))

        # Confirmation check via POST parameter
        if request.POST.get("confirm_cleanup"):
            deleted_count = to_delete.count()
            to_delete.delete()

            self.message_user(
                request,
                f"🗑️ Successfully deleted {deleted_count} non-approved import candidates.",
                messages.SUCCESS,
            )
            return HttpResponseRedirect(reverse("admin:entity_mapping_entitymapping_changelist"))

        # Show confirmation page
        from django.template.response import TemplateResponse

        # Group by entity type and status for display
        by_type = {}
        by_status = {}
        for mapping in to_delete:
            entity_type = mapping.get_entity_type_display()
            status = mapping.get_sync_status_display()
            by_type[entity_type] = by_type.get(entity_type, 0) + 1
            by_status[status] = by_status.get(status, 0) + 1

        context = dict(
            self.admin_site.each_context(request),
            title="Confirm Cleanup",
            total_count=total_count,
            by_type=by_type,
            by_status=by_status,
            action="cleanup_import_candidates",
            opts=self.model._meta,
        )

        return TemplateResponse(request, "admin/entity_mapping/confirm_bulk_action.html", context)

    cleanup_import_candidates.short_description = "🗑️ Delete ALL non-approved import candidates"

    def preview_entity_view(self, request, mapping_id):
        """Preview entity transformation before creation."""
        mapping = get_object_or_404(EntityMapping, id=mapping_id)
        service = EntityCreationService(request.user)
        preview_data = service.preview_transformation(mapping)

        # Build context with admin context for Jazzmin sidebar
        context = dict(self.admin_site.each_context(request))
        context.update(
            {
                "title": f"Preview Entity: {mapping.entity_type}",
                "mapping": mapping,
                "preview": preview_data,
                "opts": self.model._meta,
                "has_view_permission": self.has_view_permission(request),
            }
        )

        return TemplateResponse(request, "admin/entity_mapping/entity_preview.html", context)

    def create_entity_view(self, request, mapping_id):
        """Create PostgreSQL entity from mapping."""
        mapping = get_object_or_404(EntityMapping, id=mapping_id)

        if not mapping.import_approved:
            messages.error(request, "Entity mapping must be approved before creating entity.")
            return HttpResponseRedirect(reverse("admin:entity_mapping_entitymapping_changelist"))

        if mapping.postgresql_uuid:
            messages.warning(request, "PostgreSQL entity already exists for this mapping.")
            return HttpResponseRedirect(reverse("admin:entity_mapping_entitymapping_changelist"))

        service = EntityCreationService(request.user)
        result = service.create_entity_from_mapping(mapping)

        if result.success:
            messages.success(request, result.message)
        else:
            error_details = "; ".join(result.errors) if result.errors else result.message
            messages.error(request, f"Failed to create entity: {error_details}")

        # Redirect back to preview or changelist
        return HttpResponseRedirect(
            reverse("admin:entity_mapping_preview_entity", args=[mapping_id])
        )

    def changelist_view(self, request, extra_context=None):
        """Add custom URLs to changelist context and handle selection-free actions."""
        # Handle actions that don't require item selection
        if request.method == "POST":
            action = request.POST.get("action")

            # Actions that don't require selection
            if action in ["approve_all_import_candidates", "cleanup_import_candidates"]:
                # Create empty queryset and call the action directly
                empty_queryset = self.model.objects.none()

                if action == "approve_all_import_candidates":
                    return self.approve_all_import_candidates(request, empty_queryset)
                elif action == "cleanup_import_candidates":
                    return self.cleanup_import_candidates(request, empty_queryset)

        extra_context = extra_context or {}
        from django.urls import reverse

        # Add URLs for custom buttons
        extra_context["discover_candidates_url"] = reverse(
            "admin:entity_mapping_discover_candidates"
        )
        extra_context["import_candidates_url"] = reverse("admin:entity_mapping_import_candidates")
        extra_context["sync_summary_url"] = reverse("admin:entity_mapping_sync_summary")
        extra_context["sync_logs_url"] = reverse("admin:entity_mapping_synclog_changelist")

        # Add summary stats
        service = ImportCandidateService()
        summary = service.get_import_candidates_summary()
        total_candidates = sum(stats["total"] for stats in summary.values())
        total_pending = sum(stats["pending"] for stats in summary.values())

        extra_context["total_candidates"] = total_candidates
        extra_context["total_pending"] = total_pending

        return super().changelist_view(request, extra_context)

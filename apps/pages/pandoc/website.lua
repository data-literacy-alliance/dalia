-- Sanitising filter for website Markdown (see plan S2). Runs under pandoc --sandbox.
-- Four passes, applied in this order:
--   1. strip every attribute except identifier and classes
--   2. unwrap links with a non-allowlisted scheme
--   3. drop images whose src is outside /media/ and /static/
--   4. add the filter's own attributes (external links, figures, mailto)

local stringify = pandoc.utils.stringify

local ALLOWED_SCHEMES = { http = true, https = true, mailto = true, tel = true }
local INTERNAL_HOSTS = { ["dalia.education"] = true, ["www.dalia.education"] = true }

-- Remove every char <= 0x20 and 0x7f (browsers ignore them inside a scheme).
-- Backslashes become '/' as browsers treat them (so "/\\evil.com" is "//evil.com").
local function clean(target)
  local cleaned = target:gsub("[%z\1-\32\127]", "")
  return (cleaned:gsub("\\", "/"))
end

-- Text before the first '/', '?' or '#' (the only place a scheme can sit).
local function head_part(cleaned)
  return cleaned:match("^[^/?#]*")
end

local function scheme_of(cleaned)
  local head = head_part(cleaned)
  local scheme = head:match("^([^:]*):")
  if scheme then
    return scheme:lower()
  end
  return nil
end

local function is_allowed_target(cleaned)
  local scheme = scheme_of(cleaned)
  if scheme == nil then
    return true
  end
  return ALLOWED_SCHEMES[scheme] == true
end

local function host_of(cleaned)
  local authority = cleaned:match("^[%a][%w+.-]*://([^/?#\\]*)")
  if not authority then
    authority = cleaned:match("^[/\\][/\\]([^/?#\\]*)")
  end
  if not authority then
    return nil
  end
  authority = authority:gsub("^.*@", "")
  authority = authority:gsub(":%d*$", "")
  return authority:lower()
end

local function is_external(cleaned)
  local host = host_of(cleaned)
  if host == nil then
    return false
  end
  return not INTERNAL_HOSTS[host]
end

local function has_class(classes, name)
  for _, c in ipairs(classes) do
    if c == name then
      return true
    end
  end
  return false
end

-- Pass 1 ---------------------------------------------------------------
local function strip_attributes(el)
  el.attr = pandoc.Attr(el.attr.identifier, el.attr.classes, {})
  return el
end

local pass1 = {
  Div = strip_attributes,
  Span = strip_attributes,
  Header = strip_attributes,
  Link = strip_attributes,
  Image = strip_attributes,
  Code = strip_attributes,
  CodeBlock = strip_attributes,
  Table = strip_attributes,
  Figure = strip_attributes,
  Cell = strip_attributes,
  Row = strip_attributes,
  TableHead = strip_attributes,
  TableBody = strip_attributes,
  TableFoot = strip_attributes,
}

-- Pass 2 ---------------------------------------------------------------
local pass2 = {
  Link = function(el)
    local cleaned = clean(el.target)
    if not is_allowed_target(cleaned) then
      return el.content
    end
    el.target = cleaned
    return el
  end,
}

-- Pass 3 ---------------------------------------------------------------
local pass3 = {
  Image = function(el)
    local cleaned = clean(el.src)
    if cleaned:sub(1, 7) == "/media/" or cleaned:sub(1, 8) == "/static/" then
      el.src = cleaned
      return el
    end
    return pandoc.Str(stringify(el.caption))
  end,
}

-- Pass 4 ---------------------------------------------------------------
local EMAIL_PATTERN = "^(.-)([%w._%%+-]+@[%w-]+%.[%w.-]*%w)(.*)$"

local function split_email(str)
  local before, email, after = str.text:match(EMAIL_PATTERN)
  if not email then
    return nil
  end
  local out = {}
  if before ~= "" then
    table.insert(out, pandoc.Str(before))
  end
  table.insert(out, pandoc.Link(pandoc.Str(email), "mailto:" .. email, "",
    pandoc.Attr("", { "mailto" })))
  if after ~= "" then
    table.insert(out, pandoc.Str(after))
  end
  return out
end

local function style_figure_image(img)
  if img.t == "Image" then
    if not has_class(img.classes, "caption") then
      img.classes:insert("caption")
    end
    img.title = stringify(img.caption)
    return img
  end
  return nil
end

local pass4 = {
  traverse = "topdown",
  Link = function(el)
    if is_external(el.target) then
      el.attributes.target = "_blank"
      el.attributes.rel = "nofollow noopener noreferrer"
      if not has_class(el.classes, "external-link") then
        el.classes:insert("external-link")
      end
      if not has_class(el.classes, "no-image") then
        el.classes:insert("no-image")
      end
    end
    -- do not descend: no mailto links nested inside links
    return el, false
  end,
  Image = function(el)
    return el, false
  end,
  Figure = function(el)
    if not has_class(el.classes, "image-caption") then
      el.classes:insert("image-caption")
    end
    el.content = el.content:walk({ Image = style_figure_image })
    return el
  end,
  Str = function(el)
    local parts = split_email(el)
    if parts then
      -- false: do not re-visit the emitted Str/Link (would loop forever)
      return parts, false
    end
    return nil
  end,
}

return { pass1, pass2, pass3, pass4 }

-- mod-version:3
local core = require "core"
local common = require "core.common"
local command = require "core.command"
local config = require "core.config"
local keymap = require "core.keymap"
local style = require "core.style"
local View = require "core.view"
local ContextMenu = require "core.contextmenu"
local RootView = require "core.rootview"
local CommandView = require "core.commandview"

config.plugins.treeview = common.merge({
  -- Default treeview width
  size = 200 * SCALE
}, config.plugins.treeview)

local tooltip_offset = style.font:get_height()
local tooltip_border = 1
local tooltip_delay = 0.5
local tooltip_alpha = 255
local tooltip_alpha_rate = 1


local function get_depth(filename)
  local n = 1
  for _ in filename:gmatch(PATHSEP) do
    n = n + 1
  end
  return n
end

local function replace_alpha(color, alpha)
  local r, g, b = table.unpack(color)
  return { r, g, b, alpha }
end


local TreeView = View:extend()

function TreeView:__tostring() return "TreeView" end

function TreeView:new()
  TreeView.super.new(self)
  self.scrollable = true
  self.visible = true
  self.init_size = true
  self.target_size = config.plugins.treeview.size
  self.cache = {}
  self.tooltip = { x = 0, y = 0, begin = 0, alpha = 0 }
  self.cursor_pos = { x = 0, y = 0 }

  self.item_icon_width = 0
  self.item_text_spacing = 0
  
  -- Naming state (inline creation)
  self.naming = {
    active = false,
    parent_path = nil, -- absolute
    parent_rel_path = nil, -- relative to project
    parent_type = "dir",
    project_dir = nil, -- key for core.project_directories
    type = "file",
    text = "",
    rect = nil
  }
end


function TreeView:set_target_size(axis, value)
  if axis == "x" then
    self.target_size = value
    return true
  end
end


function TreeView:get_cached(dir, item, dirname)
  local dir_cache = self.cache[dirname]
  if not dir_cache then
    dir_cache = {}
    self.cache[dirname] = dir_cache
  end
  -- to discriminate top directories from regular files or subdirectories
  -- we add ':' at the end of the top directories' filename. it will be
  -- used only to identify the entry into the cache.
  local cache_name = item.filename .. (item.topdir and ":" or "")
  local t = dir_cache[cache_name]
  if not t or t.type ~= item.type then
    t = {}
    local basename = common.basename(item.filename)
    if item.topdir then
      t.filename = basename
      t.expanded = true
      t.depth = 0
      t.abs_filename = dirname
    else
      t.filename = item.filename
      t.depth = get_depth(item.filename)
      t.abs_filename = dirname .. PATHSEP .. item.filename
    end
    t.name = basename
    t.type = item.type
    t.dir_name = dir.name -- points to top level "dir" item
    dir_cache[cache_name] = t
  end
  return t
end


function TreeView:get_name()
  return nil
end


function TreeView:get_item_height()
  return style.font:get_height() + style.padding.y
end


function TreeView:invalidate_cache(dirname)
  for _, v in pairs(self.cache[dirname]) do
    v.skip = nil
  end
end


function TreeView:check_cache()
  for i = 1, #core.project_directories do
    local dir = core.project_directories[i]
    -- invalidate cache's skip values if directory is declared dirty
    if dir.is_dirty and self.cache[dir.name] then
      self:invalidate_cache(dir.name)
    end
    dir.is_dirty = false
  end
end


function TreeView:each_item()
  return coroutine.wrap(function()
    self:check_cache()
    local count_lines = 0
    local ox, oy = self:get_content_offset()
    local y = oy + style.padding.y
    local w = self.size.x
    local h = self:get_item_height()

    -- Draw "EXPLORER" header
    local header_h = style.font:get_height() + style.padding.y * 2
    y = y + header_h

    for k = 1, #core.project_directories do
      local dir = core.project_directories[k]
      local dir_cached = self:get_cached(dir, dir.item, dir.name)
      coroutine.yield(dir_cached, ox, y, w, h)
      count_lines = count_lines + 1
      y = y + h
      -- 4. Inject Naming Input row if active for this directory
      if self.naming.active and self.naming.parent_path == dir_cached.abs_filename then
        coroutine.yield({ naming = true, depth = 1, type = self.naming.type }, ox, y, w, h)
        y = y + h
        count_lines = count_lines + 1
      end

      local i = 1
      if dir.files then -- if consumed max sys file descriptors this can be nil
        while i <= #dir.files and dir_cached.expanded do
          local item = dir.files[i]
          local cached = self:get_cached(dir, item, dir.name)

          coroutine.yield(cached, ox, y, w, h)
          count_lines = count_lines + 1
          y = y + h
          i = i + 1
          
          -- 5. Inject Naming Input row for subfolders
          if self.naming.active and self.naming.parent_path == cached.abs_filename then
            coroutine.yield({ naming = true, depth = cached.depth + 1, type = self.naming.type }, ox, y, w, h)
            y = y + h
            count_lines = count_lines + 1
          end

          if not cached.expanded then
            if cached.skip then
              i = cached.skip
            else
              local depth = cached.depth
              while i <= #dir.files do
                if get_depth(dir.files[i].filename) <= depth then break end
                i = i + 1
              end
              cached.skip = i
            end
          end
        end -- while files
      end
    end -- for directories
    self.count_lines = count_lines
  end)
end


function TreeView:set_selection(selection, selection_y)
  self.selected_item = selection
  if selection and selection_y
      and (selection_y <= 0 or selection_y >= self.size.y) then

    local lh = self:get_item_height()
    if selection_y >= self.size.y - lh then
      selection_y = selection_y - self.size.y + lh
    end
    local _, y = self:get_content_offset()
    self.scroll.to.y = selection and (selection_y - y)
  end
end


function TreeView:get_text_bounding_box(item, x, y, w, h)
  if item.naming then
    return x, y, w, h
  end
  local icon_width = style.icon_font:get_width("D")
  local xoffset = item.depth * style.padding.x + style.padding.x + icon_width
  x = x + xoffset
  local text_w = style.font:get_width(item.name) + 2 * style.padding.x
  
  -- If project folder, leave space for action icons on the right
  if item.depth == 0 then
    local action_w = (style.icon_font:get_width("f") + style.padding.x) * 4 + style.padding.x
    w = math.min(text_w, w - xoffset - action_w)
  else
    w = text_w
  end
  return x, y, w, h
end


function TreeView:on_mouse_moved(px, py, ...)
  if not self.visible then return end
  self.cursor_pos.x = px
  self.cursor_pos.y = py
  if TreeView.super.on_mouse_moved(self, px, py, ...) then
    -- mouse movement handled by the View (scrollbar)
    self.hovered_item = nil
    return
  end

  local item_changed, tooltip_changed, icon_changed
  for item, x,y,w,h in self:each_item() do
    if px > x and py > y and px <= x + w and py <= y + h then
      item_changed = true
      self.hovered_item = item
      
      -- Action Icons Hit Test
      if item.action_icons then
        for _, icon in ipairs(item.action_icons) do
          if px >= icon.rect.x and py >= icon.rect.y and px < icon.rect.x + icon.rect.w and py < icon.rect.y + icon.rect.h then
            self.hovered_icon = icon.cmd
            icon_changed = true
            break
          end
        end
      end

      x,y,w,h = self:get_text_bounding_box(item, x,y,w,h)
      if px > x and py > y and px <= x + w and py <= y + h then
        tooltip_changed = true
        self.tooltip.x, self.tooltip.y = px, py
        self.tooltip.begin = system.get_time()
      end
      break
    end
  end
  if not item_changed then self.hovered_item = nil end
  if not tooltip_changed then self.tooltip.x, self.tooltip.y = nil, nil end
  if not icon_changed then self.hovered_icon = nil end
end


function TreeView:update()
  -- update width
  local dest = self.visible and self.target_size or 0
  if self.init_size then
    self.size.x = dest
    self.init_size = false
  else
    self:move_towards(self.size, "x", dest, nil, "treeview")
  end

  if not self.visible then return end

  local duration = system.get_time() - self.tooltip.begin
  if self.hovered_item and self.tooltip.x and duration > tooltip_delay then
    self:move_towards(self.tooltip, "alpha", tooltip_alpha, tooltip_alpha_rate, "treeview")
  else
    self.tooltip.alpha = 0
  end

  self.item_icon_width = style.icon_font:get_width("D")
  self.item_text_spacing = style.icon_font:get_width("f") / 2

  -- this will make sure hovered_item is updated
  -- we don't want events when the thing is scrolling fast
  local dy = math.abs(self.scroll.to.y - self.scroll.y)
  if self.scroll.to.y ~= 0 and dy < self:get_item_height() then
    self:on_mouse_moved(self.cursor_pos.x, self.cursor_pos.y, 0, 0)
  end

  TreeView.super.update(self)
end

function TreeView:on_text_input(text)
  if self.naming.active then
    self.naming.text = self.naming.text .. text
    core.redraw = true
    return true
  end
end

function TreeView:on_key_pressed(k)
  if self.naming.active then
    core.log_quiet("TreeView Key: %s", k)
    if k == "backspace" then
      self.naming.text = self.naming.text:sub(1, -2)
      core.redraw = true
    elseif k == "return" or k == "keypad enter" or k == "enter" then
      local name = self.naming.text
      core.log("TreeView: Submitting %q", name)
      
      if name ~= "" then
        local path = self.naming.parent_path
        local rel_path = self.naming.parent_rel_path
        if self.naming.parent_type == "file" then
          path = common.dirname(path) or path
          rel_path = common.dirname(rel_path) or ""
        end
        local full_path = path .. PATHSEP .. name
        
        core.log("TreeView: Path -> %s", full_path)
        
        -- Creation Logic
        local ok, err = pcall(function()
          if self.naming.type == "file" then
            local f = io.open(full_path, "a+")
            if f then f:close() end
            core.root_view:open_doc(core.open_doc(full_path))
          else
            common.mkdirp(full_path)
          end
        end)
        
        if ok then
          core.log("TreeView: Success! Refreshing tree.")
          local project = core.project_dir_by_name(self.naming.project_dir)
          if project then
            project.is_dirty = true
            if project.files_limit then
              core.update_project_subdir(project, rel_path, true)
            end
          end
        else
          core.error("TreeView: Creation failed: %s", tostring(err))
          -- Fallback: Try PowerShell if Lua fails
          local itype = (self.naming.type == "file") and "File" or "Directory"
          local cmd = string.format('powershell -Command "New-Item -Path \'%s\' -ItemType %s -Force"', full_path, itype)
          os.execute(cmd)
        end
      end
      
      self.naming.active = false
      self.hovered_item = nil
      core.redraw = true
    elseif k == "escape" then
      core.log("TreeView: Cancelled")
      self.naming.active = false
      self.hovered_item = nil
      core.redraw = true
    end
    return true
  end
  return TreeView.super.on_key_pressed(self, k)
end


function TreeView:get_scrollable_size()
  local header_h = style.font:get_height() + style.padding.y * 2
  return self.count_lines and (self:get_item_height() * self.count_lines + header_h + style.padding.y) or math.huge
end


function TreeView:draw_tooltip()
  if not self.hovered_item or not self.hovered_item.abs_filename then return end
  local text = common.home_encode(self.hovered_item.abs_filename)
  local w, h = style.font:get_width(text), style.font:get_height(text)

  local x, y = self.tooltip.x + tooltip_offset, self.tooltip.y + tooltip_offset
  w, h = w + style.padding.x, h + style.padding.y

  if x + w > core.root_view.root_node.size.x then -- check if we can span right
    x = x - w -- span left instead
  end

  local bx, by = x - tooltip_border, y - tooltip_border
  local bw, bh = w + 2 * tooltip_border, h + 2 * tooltip_border
  renderer.draw_rect(bx, by, bw, bh, replace_alpha(style.text, self.tooltip.alpha))
  renderer.draw_rect(x, y, w, h, replace_alpha(style.background2, self.tooltip.alpha))
  common.draw_text(style.font, replace_alpha(style.text, self.tooltip.alpha), text, "center", x, y, w, h)
end


function TreeView:get_item_icon(item, active, hovered)
  local character = "f"
  if item.type == "dir" then
    character = item.expanded and "D" or "d"
  end
  local font = style.icon_font
  local color = style.text
  if active or hovered then
    color = style.accent
  end
  return character, font, color
end

function TreeView:get_item_text(item, active, hovered)
  local text = item.name
  local font = style.font
  local color = style.text
  if active or hovered then
    color = style.accent
  end
  return text, font, color
end


function TreeView:draw_item_text(item, active, hovered, x, y, w, h)
  local item_text, item_font, item_color = self:get_item_text(item, active, hovered)
  -- Use bound width for truncation
  local _, _, bound_w = self:get_text_bounding_box(item, x, y, w, h)
  common.draw_text(item_font, item_color, item_text, nil, x, y, bound_w, h)
end


function TreeView:draw_item_icon(item, active, hovered, x, y, w, h)
  local icon_char, icon_font, icon_color = self:get_item_icon(item, active, hovered)
  common.draw_text(icon_font, icon_color, icon_char, nil, x, y, 0, h)
  return self.item_icon_width + self.item_text_spacing
end


function TreeView:draw_item_body(item, active, hovered, x, y, w, h)
    x = x + self:draw_item_icon(item, active, hovered, x, y, w, h)
    self:draw_item_text(item, active, hovered, x, y, w, h)
end


function TreeView:draw_item_chevron(item, active, hovered, x, y, w, h)
  if item.type == "dir" then
    local chevron_icon = item.expanded and "-" or "+"
    local chevron_color = hovered and style.accent or style.text
    common.draw_text(style.icon_font, chevron_color, chevron_icon, nil, x, y, 0, h)
  end
  return style.padding.x
end


function TreeView:draw_item_background(item, active, hovered, x, y, w, h)
  if hovered then
    local hover_color = { table.unpack(style.line_highlight) }
    hover_color[4] = 160
    renderer.draw_rect(x, y, w, h, hover_color)
  elseif active then
    renderer.draw_rect(x, y, w, h, style.line_highlight)
  end
end


function TreeView:draw_item(item, active, hovered, x, y, w, h)
  if item.naming then
    self:draw_naming_input(item, x, y, w, h)
    return
  end
  self:draw_item_background(item, active, hovered, x, y, w, h)

  x = x + item.depth * style.padding.x + style.padding.x
  x = x + self:draw_item_chevron(item, active, hovered, x, y, w, h)

  self:draw_item_body(item, active, hovered, x, y, w, h)
  
  -- Draw Action Icons for project folders
  if item.depth == 0 and (hovered or self.hovered_item == item) then
    local icon_font = style.icon_font
    local icon_w = icon_font:get_width("f")
    local spacing = style.padding.x
    local icon_group_w = (icon_w + spacing) * 4 + style.padding.x
    local right_start_x = x + w - icon_group_w
    
    -- Draw Solid Background for icons to prevent transparency issues
    renderer.draw_rect(right_start_x, y, icon_group_w, h, hovered and style.line_highlight or style.background2)
    
    local icons = {
      { char = "f", cmd = "treeview:new-file", tooltip = "New File" },
      { char = "d", cmd = "treeview:new-folder", tooltip = "New Folder" },
      { char = "i", cmd = "treeview:refresh", tooltip = "Refresh" },
      { char = "v", cmd = "treeview:collapse-all", tooltip = "Collapse All" }
    }
    
    for i, icon in ipairs(icons) do
      local ix = right_start_x + style.padding.x + (i-1) * (icon_w + spacing)
      local icol = (self.hovered_icon == icon.cmd) and style.accent or style.text
      common.draw_text(icon_font, icol, icon.char, nil, ix, y, 0, h)
      
      -- Store rect for hit testing (relative to screen)
      icon.rect = { x = ix, y = y, w = icon_w, h = h }
      item.action_icons = item.action_icons or {}
      item.action_icons[i] = icon
    end
  end
end

function TreeView:draw_naming_input(item, x, y, w, h)
  local depth_padding = item.depth * style.padding.x + style.padding.x
  
  -- Draw Icon
  x = x + depth_padding
  local icon_w = self:draw_item_icon({ type = item.type }, false, false, x, y, w, h)
  x = x + icon_w
  
  -- Draw Input Box
  local input_x = x
  local input_w = self.size.x - (input_x - self.position.x) - style.padding.x
  local input_h = style.font:get_height() + style.padding.y / 2
  local input_y = y + (h - input_h) / 2
  
  -- VS Code blue border
  local border_col = { common.color "#007acc" }
  renderer.draw_rect(input_x - 1, input_y - 1, input_w + 2, input_h + 2, border_col)
  renderer.draw_rect(input_x, input_y, input_w, input_h, style.background)
  
  -- Text
  local text = self.naming.text .. "|" -- Caret simulation
  common.draw_text(style.font, style.text, text, nil, input_x + 2, input_y, input_w - 4, input_h)
  
  -- Store input rect for hit testing in RootView
  self.naming.rect = { x = input_x, y = input_y, w = input_w, h = input_h }
end


function TreeView:draw()
  if not self.visible then return end
  self:draw_background(style.background2)
  local _y, _h = self.position.y, self.size.y

  -- Draw Static Header
  local header_h = style.font:get_height() + style.padding.y * 2
  renderer.draw_rect(self.position.x, self.position.y, self.size.x, header_h, style.background2)
  local header_text_y = self.position.y + style.padding.y
  common.draw_text(style.font, style.dim, "EXPLORER", nil, self.position.x + style.padding.x, header_text_y, 0, header_h)
  -- Bottom border for header
  renderer.draw_rect(self.position.x, self.position.y + header_h - 1, self.size.x, 1, style.line_highlight)

  for item, x,y,w,h in self:each_item() do
    if y + h >= _y + header_h and y < _y + _h then
      self:draw_item(item,
        item == self.selected_item,
        item == self.hovered_item,
        x, y, w, h)
    end
  end

  self:draw_scrollbar()
  if self.hovered_item and self.tooltip.x and self.tooltip.alpha > 0 then
    core.root_view:defer_draw(self.draw_tooltip, self)
  end
end


function TreeView:get_parent(item)
  local parent_path = common.dirname(item.abs_filename)
  if not parent_path then return end
  for it, _, y in self:each_item() do
    if it.abs_filename == parent_path then
      return it, y
    end
  end
end


function TreeView:get_item(item, where)
  local last_item, last_x, last_y, last_w, last_h
  local stop = false

  for it, x, y, w, h in self:each_item() do
    if not item and where >= 0 then
      return it, x, y, w, h
    end
    if item == it then
      if where < 0 and last_item then
        break
      elseif where == 0 or (where < 0 and not last_item) then
        return it, x, y, w, h
      end
      stop = true
    elseif stop then
      item = it
      return it, x, y, w, h
    end
    last_item, last_x, last_y, last_w, last_h = it, x, y, w, h
  end
  return last_item, last_x, last_y, last_w, last_h
end

function TreeView:get_next(item)
  return self:get_item(item, 1)
end

function TreeView:get_previous(item)
  return self:get_item(item, -1)
end


function TreeView:toggle_expand(toggle)
  local item = self.selected_item

  if not item then return end

  if item.type == "dir" then
    if type(toggle) == "boolean" then
      item.expanded = toggle
    else
      item.expanded = not item.expanded
    end
    local hovered_dir = core.project_dir_by_name(item.dir_name)
    if hovered_dir and hovered_dir.files_limit then
      core.update_project_subdir(hovered_dir, item.depth == 0 and "" or item.filename, item.expanded)
    end
  end
end


-- init
local view = TreeView()
local node = core.root_view:get_active_node()
view.node = node:split("left", view, {x = true}, true)

-- The toolbarview plugin is special because it is plugged inside
-- a treeview pane which is itelf provided in a plugin.
-- We therefore break the usual plugin's logic that would require each
-- plugin to be independent of each other. In addition it is not the
-- plugin module that plug itself in the active node but it is plugged here
-- in the treeview node.
local toolbar_view = nil
local toolbar_plugin, ToolbarView = pcall(require, "plugins.toolbarview")
if config.plugins.toolbarview ~= false and toolbar_plugin then
  toolbar_view = ToolbarView()
  view.node:split("down", toolbar_view, {y = true})
  local min_toolbar_width = toolbar_view:get_min_width()
  view:set_target_size("x", math.max(config.plugins.treeview.size, min_toolbar_width))
  command.add(nil, {
    ["toolbar:toggle"] = function()
      toolbar_view:toggle_visible()
    end,
  })
end

-- Add a context menu to the treeview
local menu = ContextMenu()

local on_view_mouse_pressed = RootView.on_view_mouse_pressed
local on_mouse_moved = RootView.on_mouse_moved
local root_view_update = RootView.update
local root_view_draw = RootView.draw
local keymap = require "core.keymap"
local keymap_on_key_pressed = keymap.on_key_pressed

function keymap.on_key_pressed(k, ...)
  if view.naming.active and (k == "return" or k == "keypad enter" or k == "enter") then
    view:on_key_pressed(k)
    return true
  end
  return keymap_on_key_pressed(k, ...)
end

function RootView:on_mouse_moved(...)
  if menu:on_mouse_moved(...) then return end
  on_mouse_moved(self, ...)
end

function RootView.on_view_mouse_pressed(button, x, y, clicks)
  if view.naming.active then
    local r = view.naming.rect
    if not r or not (x >= r.x and x < r.x + r.w and y >= r.y and y < r.y + r.h) then
      view.naming.active = false
      core.redraw = true
    end
  end

  -- Check for TreeView action icons first
  if core.active_view:is(TreeView) and core.active_view.hovered_icon then
    command.perform(core.active_view.hovered_icon, core.active_view.hovered_icon_item)
    return true
  end

  -- We give the priority to the menu to process mouse pressed events.
  if button == "right" then
    view.tooltip.alpha = 0
    view.tooltip.x, view.tooltip.y = nil, nil
  end
  local handled = menu:on_mouse_pressed(button, x, y, clicks)
  return handled or on_view_mouse_pressed(button, x, y, clicks)
end

function RootView:update(...)
  root_view_update(self, ...)
  menu:update()
end

function RootView:draw(...)
  root_view_draw(self, ...)
  menu:draw()
end

local on_quit_project = core.on_quit_project
function core.on_quit_project()
  view.cache = {}
  on_quit_project()
end

local function is_project_folder(path)
  for _,dir in pairs(core.project_directories) do
    if dir.name == path then
      return true
    end
  end
  return false
end

local function is_primary_project_folder(path)
  return core.project_dir == path
end


local function treeitem() return view.hovered_item or view.selected_item end


menu:register(function() return core.active_view:is(TreeView) and treeitem() end, {
  { text = "Open in System", command = "treeview:open-in-system" },
  ContextMenu.DIVIDER
})

menu:register(
  function()
    local item = treeitem()
    return core.active_view:is(TreeView) and item and not is_project_folder(item.abs_filename)
  end,
  {
    { text = "Rename", command = "treeview:rename" },
    { text = "Delete", command = "treeview:delete" },
  }
)

menu:register(
  function()
    local item = treeitem()
    return core.active_view:is(TreeView) and item and item.type == "dir"
  end,
  {
    { text = "New File", command = "treeview:new-file" },
    { text = "New Folder", command = "treeview:new-folder" },
  }
)

menu:register(
  function()
    local item = treeitem()
    return core.active_view:is(TreeView) and item
      and not is_primary_project_folder(item.abs_filename)
      and is_project_folder(item.abs_filename)
  end,
  {
    { text = "Remove directory", command = "treeview:remove-project-directory" },
  }
)

local previous_view = nil

-- Register the TreeView commands and keymap
command.add(nil, {
  ["treeview:toggle"] = function()
    view.visible = not view.visible
  end,

  ["treeview:toggle-focus"] = function()
    if not core.active_view:is(TreeView) then
      if core.active_view:is(CommandView) then
        previous_view = core.last_active_view
      else
        previous_view = core.active_view
      end
      if not previous_view then
        previous_view = core.root_view:get_primary_node().active_view
      end
      core.set_active_view(view)
      if not view.selected_item then
        for it, _, y in view:each_item() do
          view:set_selection(it, y)
          break
        end
      end

    else
      core.set_active_view(
        previous_view or core.root_view:get_primary_node().active_view
      )
    end
  end,

  ["treeview:collapse-all"] = function()
    for _, dir_cache in pairs(view.cache) do
      for _, item in pairs(dir_cache) do
        if item.type == "dir" then
          item.expanded = false
        end
      end
    end
    core.redraw = true
  end,

  ["treeview:refresh"] = function()
    for _, dir in ipairs(core.project_directories) do
      dir.is_dirty = true
    end
    core.redraw = true
    core.log_quiet("Project refreshed")
  end
})

command.add(
  function()
    return not menu.show_context_menu and core.active_view:extends(TreeView), TreeView
  end, {
  ["treeview:next"] = function()
    local item, _, item_y = view:get_next(view.selected_item)
    view:set_selection(item, item_y)
  end,

  ["treeview:previous"] = function()
    local item, _, item_y = view:get_previous(view.selected_item)
    view:set_selection(item, item_y)
  end,

  ["treeview:open"] = function()
    local item = view.selected_item
    if not item then return end
    if item.type == "dir" then
      view:toggle_expand()
    else
      core.try(function()
        if core.last_active_view and core.active_view == view then
          core.set_active_view(core.last_active_view)
        end
        local doc_filename = core.normalize_to_project_dir(item.abs_filename)
        core.root_view:open_doc(core.open_doc(doc_filename))
      end)
    end
  end,

  ["treeview:deselect"] = function()
    view.selected_item = nil
  end,

  ["treeview:select"] = function()
    view:set_selection(view.hovered_item)
  end,

  ["treeview:select-and-open"] = function()
    if view.hovered_item then
      view:set_selection(view.hovered_item)
      command.perform "treeview:open"
    end
  end,

  ["treeview:collapse"] = function()
    if view.selected_item then
      if view.selected_item.type == "dir" and view.selected_item.expanded then
        view:toggle_expand(false)
      else
        local parent_item, y = view:get_parent(view.selected_item)
        if parent_item then
          view:set_selection(parent_item, y)
        end
      end
    end
  end,

  ["treeview:expand"] = function()
    local item = view.selected_item
    if not item or item.type ~= "dir" then return end

    if item.expanded then
      local next_item, _, next_y = view:get_next(item)
      if next_item.depth > item.depth then
        view:set_selection(next_item, next_y)
      end
    else
      view:toggle_expand(true)
    end
  end,
})


command.add(
  function()
    local item = treeitem()
    return item ~= nil and (core.active_view == view or menu.show_context_menu), item
  end, {
  ["treeview:delete"] = function(item)
    local filename = item.abs_filename
    local relfilename = item.filename
    if item.dir_name ~= core.project_dir then
      -- add secondary project dirs names to the file path to show
      relfilename = common.basename(item.dir_name) .. PATHSEP .. relfilename
    end
    local file_info = system.get_file_info(filename)
    local file_type = file_info.type == "dir" and "Directory" or "File"
    -- Ask before deleting
    local opt = {
      { text = "Yes", default_yes = true },
      { text = "No", default_no = true }
    }
    core.nag_view:show(
      string.format("Delete %s", file_type),
      string.format(
        "Are you sure you want to delete the %s?\n%s: %s",
        file_type:lower(), file_type, relfilename
      ),
      opt,
      function(item)
        if item.text == "Yes" then
          if file_info.type == "dir" then
            local deleted, error, path = common.rm(filename, true)
            if not deleted then
              core.error("Error: %s - \"%s\" ", error, path)
              return
            end
          else
            local removed, error = os.remove(filename)
            if not removed then
              core.error("Error: %s - \"%s\"", error, filename)
              return
            end
          end
          core.log("Deleted \"%s\"", filename)
        end
      end
    )
  end,

  ["treeview:rename"] = function(item)
    local old_filename = item.filename
    local old_abs_filename = item.abs_filename
    core.command_view:enter("Rename", {
      text = old_filename,
      submit = function(filename)
        local abs_filename = filename
        if not common.is_absolute_path(filename) then
          abs_filename = item.dir_name .. PATHSEP .. filename
        end
        local res, err = os.rename(old_abs_filename, abs_filename)
        if res then -- successfully renamed
          for _, doc in ipairs(core.docs) do
            if doc.abs_filename and old_abs_filename == doc.abs_filename then
              doc:set_filename(filename, abs_filename) -- make doc point to the new filename
              doc:reset_syntax()
              break -- only first needed
            end
          end
          core.log("Renamed \"%s\" to \"%s\"", old_filename, filename)
        else
          core.error("Error while renaming \"%s\" to \"%s\": %s", old_abs_filename, abs_filename, err)
        end
      end,
      suggest = function(text)
        return common.path_suggest(text, item.dir_name)
      end
    })
  end,

  ["treeview:new-file"] = function(item)
    if not item then
      local dir = core.project_directories[1]
      item = dir and view:get_cached(dir, dir.item, dir.name)
    end
    if not item then return end
    if item.type == "dir" then item.expanded = true end
    view.naming.active = true
    view.naming.parent_path = item.abs_filename
    -- Fix: if it's the root directory, relative path should be ""
    local rel_path = ""
    for _, dir in ipairs(core.project_directories) do
      if dir.name == item.dir_name then
        if item.abs_filename ~= dir.name then
          rel_path = item.filename
        end
        break
      end
    end
    view.naming.parent_rel_path = rel_path
    view.naming.parent_type = item.type
    view.naming.project_dir = item.dir_name
    view.naming.type = "file"
    view.naming.text = ""
    core.set_active_view(view)
    core.redraw = true
  end,

  ["treeview:new-folder"] = function(item)
    if not item then
      local dir = core.project_directories[1]
      item = dir and view:get_cached(dir, dir.item, dir.name)
    end
    if not item then return end
    if item.type == "dir" then item.expanded = true end
    view.naming.active = true
    view.naming.parent_path = item.abs_filename
    -- Fix: if it's the root directory, relative path should be ""
    local rel_path = ""
    for _, dir in ipairs(core.project_directories) do
      if dir.name == item.dir_name then
        if item.abs_filename ~= dir.name then
          rel_path = item.filename
        end
        break
      end
    end
    view.naming.parent_rel_path = rel_path
    view.naming.parent_type = item.type
    view.naming.project_dir = item.dir_name
    view.naming.type = "dir"
    view.naming.text = ""
    core.set_active_view(view)
    core.redraw = true
  end,

  ["treeview:open-in-system"] = function(item)
    if PLATFORM == "Windows" then
      system.exec(string.format("start \"\" %q", item.abs_filename))
    elseif string.find(PLATFORM, "Mac") then
      system.exec(string.format("open %q", item.abs_filename))
    elseif PLATFORM == "Linux" or string.find(PLATFORM, "BSD") then
      system.exec(string.format("xdg-open %q", item.abs_filename))
    end
  end
})

local projectsearch = pcall(require, "plugins.projectsearch")
if projectsearch then
  menu:register(function()
    local item = treeitem()
    return item and item.type == "dir"
  end, { 
    { text = "Find in directory", command = "treeview:search-in-directory" } 
  })
  command.add(function()
    return view.hovered_item and view.hovered_item.type == "dir"
  end, {
    ["treeview:search-in-directory"] = function(item)
      command.perform("project-search:find", view.hovered_item.abs_filename)
    end
  })
end

command.add(function()
    local item = treeitem()
    return item
           and not is_primary_project_folder(item.abs_filename)
           and is_project_folder(item.abs_filename), item
  end, {
  ["treeview:remove-project-directory"] = function(item)
    core.remove_project_directory(item.dir_name)
  end,
})


keymap.add {
  ["ctrl+\\"]     = "treeview:toggle",
  ["up"]          = "treeview:previous",
  ["down"]        = "treeview:next",
  ["left"]        = "treeview:collapse",
  ["right"]       = "treeview:expand",
  ["return"]      = "treeview:open",
  ["escape"]      = "treeview:deselect",
  ["delete"]      = "treeview:delete",
  ["ctrl+return"] = "treeview:new-folder",
  ["lclick"]      = "treeview:select-and-open",
  ["mclick"]      = "treeview:select",
  ["ctrl+lclick"] = "treeview:new-folder"
}

-- The config specification used by gui generators
config.plugins.treeview.config_spec = {
  name = "Treeview",
  {
    label = "Size",
    description = "Default treeview width.",
    path = "size",
    type = "number",
    default = toolbar_view and math.ceil(toolbar_view:get_min_width() / SCALE)
      or 200 * SCALE,
    min = toolbar_view and toolbar_view:get_min_width() / SCALE
      or 200 * SCALE,
    get_value = function(value)
      return value / SCALE
    end,
    set_value = function(value)
      return value * SCALE
    end,
    on_apply = function(value)
      view:set_target_size("x", math.max(
        value, toolbar_view and toolbar_view:get_min_width() or 200 * SCALE
      ))
    end
  },
  {
    label = "Hide on Startup",
    description = "Show or hide the treeview on startup.",
    path = "visible",
    type = "toggle",
    default = false,
    on_apply = function(value)
      view.visible = not value
    end
  }
}

-- Return the treeview with toolbar and contextmenu to allow
-- user or plugin modifications
view.toolbar = toolbar_view
view.contextmenu = menu

return view

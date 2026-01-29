local core = require "core"
local common = require "core.common"
local style = require "core.style"
local View = require "core.view"
local ContextMenu = require "core.contextmenu"

local icon_colors = {
  bg = { common.color "#2e2e32ff" },
  color6 = { common.color "#e1e1e6ff" },
  color7 = { common.color "#ffa94dff" },
  color8 = { common.color "#93ddfaff" },
  color9 = { common.color "#f7c95cff" }
};

local restore_command = {
  symbol = "w", action = function() system.set_window_mode("normal") end
}

local maximize_command = {
  symbol = "W", action = function() system.set_window_mode("maximized") end
}

local title_commands = {
  {symbol = "_", action = function() system.set_window_mode("minimized") end},
  maximize_command,
  {symbol = "X", action = function() core.quit() end},
}

---@class core.titleview : core.view
---@field super core.view
local TitleView = View:extend()

function TitleView:__tostring() return "TitleView" end

local function title_view_height()
  return style.font:get_height() + style.padding.y * 2
end

function TitleView:new()
  TitleView.super.new(self)
  self.visible = true
  self.hovered_menu = nil
  self.menu_context = ContextMenu()
  self.menu_items = {
    { text = "File", items = {
      { text = "New Text File", command = "core:new-doc", info = "Ctrl+N" },
      { text = "New File...", command = "core:new-named-doc" },
      { text = "New Window", command = "core:restart" }, 
      ContextMenu.DIVIDER,
      { text = "Open File...", command = "core:open-file", info = "Ctrl+O" },
      { text = "Open Folder...", command = "core:open-project-folder" },
      -- { text = "Open Recent", command = "core:open-recent" }, -- Nested menus not fully supported yet in this simple implementation
      ContextMenu.DIVIDER,
      { text = "Add Folder to Workspace...", command = "core:add-directory" },
      { text = "Save Workspace As...", command = "core:open-project-module" }, -- closest approximation
      ContextMenu.DIVIDER,
      { text = "Save", command = "doc:save", info = "Ctrl+S" },
      { text = "Save As...", command = "doc:save-as", info = "Ctrl+Shift+S" },
      ContextMenu.DIVIDER,
      { text = "Auto Save", command = "autosave:toggle" }, -- Assumes autosave plugin adds this
      { text = "Preferences", command = "core:open-user-module" },
      ContextMenu.DIVIDER,
      { text = "Close Editor", command = "doc:close", info = "Ctrl+W" },
      { text = "Close Folder", command = "core:remove-directory" },
      { text = "Close Window", command = "core:quit", info = "Alt+F4" },
      { text = "Exit", command = "core:quit" },
    }},
    { text = "Edit", items = {
      { text = "Undo", command = "doc:undo" },
      { text = "Redo", command = "doc:redo" },
      ContextMenu.DIVIDER,
      { text = "Cut", command = "doc:cut" },
      { text = "Copy", command = "doc:copy" },
      { text = "Paste", command = "doc:paste" },
      ContextMenu.DIVIDER,
      { text = "Find", command = "find-replace:find" },
      { text = "Replace", command = "find-replace:replace" },
    }},
    { text = "View", items = {
      { text = "Command Palette", command = "core:find-command" },
      { text = "Toggle Sidebar", command = "treeview:toggle" },
      { text = "Toggle Log", command = "core:toggle-log" },
    }},
    { text = "Help", items = {
      { text = "About", command = "core:about" },
    }}
  }
  self.menu_rects = {}
end

function TitleView:configure_hit_test(borderless)
  if borderless then
    local title_height = title_view_height()
    local icon_w = style.icon_font:get_width("_")
    local icon_spacing = icon_w
    local controls_width = (icon_w + icon_spacing) * #title_commands + icon_spacing
    -- system.set_window_hit_test(title_height, controls_width, icon_spacing)
    -- core.hit_test_title_height = title_height
  else
    system.set_window_hit_test()
  end
end

function TitleView:on_scale_change()
  self:configure_hit_test(self.visible)
end

function TitleView:update()
  self.size.y = self.visible and title_view_height() or 0
  title_commands[2] = core.window_mode == "maximized" and restore_command or maximize_command
  self.menu_context:update()
  TitleView.super.update(self)
end


function TitleView:draw_window_title()
  local h = style.font:get_height()
  local ox, oy = self:get_content_offset()
  local x, y = ox + style.padding.x, oy + style.padding.y
  common.draw_text(style.icon_font, icon_colors.bg, "5", nil, x, y, 0, h)
  common.draw_text(style.icon_font, icon_colors.color6, "6", nil, x, y, 0, h)
  common.draw_text(style.icon_font, icon_colors.color7, "7", nil, x, y, 0, h)
  common.draw_text(style.icon_font, icon_colors.color8, "8", nil, x, y, 0, h)
  x = common.draw_text(style.icon_font, icon_colors.color9, "9 ", nil, x, y, 0, h)
  
  -- Draw menu items
  self.menu_rects = {}
  for i, menu in ipairs(self.menu_items) do
    local menu_color = (self.hovered_menu == i) and style.accent or style.text
    local item_w = style.font:get_width(menu.text)
    local draw_x = x
    x = common.draw_text(style.font, menu_color, menu.text, nil, x, y, 0, h)
    
    table.insert(self.menu_rects, {
      x = draw_x, 
      y = y, 
      w = item_w, 
      h = h, 
      items = menu.items
    })
    x = x + style.padding.x * 2 
  end
end

function TitleView:each_control_item()
  local icon_h, icon_w = style.icon_font:get_height(), style.icon_font:get_width("_")
  local icon_spacing = icon_w
  local ox, oy = self:get_content_offset()
  ox = ox + self.size.x
  local i, n = 0, #title_commands
  local iter = function()
    i = i + 1
    if i <= n then
      local dx = - (icon_w + icon_spacing) * (n - i + 1)
      local dy = style.padding.y
      return title_commands[i], ox + dx, oy + dy, icon_w, icon_h
    end
  end
  return iter
end


function TitleView:draw_window_controls()
  for item, x, y, w, h in self:each_control_item() do
    local color = item == self.hovered_item and style.text or style.dim
    common.draw_text(style.icon_font, color, item.symbol, nil, x, y, 0, h)
  end
end


function TitleView:on_mouse_pressed(button, x, y, clicks)
  if self.menu_context:on_mouse_pressed(button, x, y, clicks) then return true end
  
  -- Handle menu opening on left click before window dragging (super)
  if self.hovered_menu and button == "left" then
    local menu_idx = self.hovered_menu
    local rect = self.menu_rects[menu_idx]
    if rect then
      self.menu_context.itemset = {}
      self.menu_context:register(function() return true end, rect.items)
      self.menu_context:show(rect.x, rect.y + rect.h + style.padding.y)
      return true
    end
  end

  local caught = TitleView.super.on_mouse_pressed(self, button, x, y, clicks)
  if caught then return end
  core.set_active_view(core.last_active_view)
  
  if self.hovered_item then
    self.hovered_item.action()
    return true
  end
end


function TitleView:on_mouse_moved(px, py, ...)
  if self.menu_context:on_mouse_moved(px, py, ...) then return true end
  
  if self.size.y == 0 then return end
  TitleView.super.on_mouse_moved(self, px, py, ...)
  self.hovered_item = nil
  self.hovered_menu = nil
  
  -- Check window controls
  for item, x, y, w, h in self:each_control_item() do
    if px > x and py > y and px <= x + w and py <= y + h then
      self.hovered_item = item
      return
    end
  end
  
  -- Check menu items
  for i, rect in ipairs(self.menu_rects) do
    if px >= rect.x and px <= rect.x + rect.w and py >= rect.y and py <= rect.y + rect.h then
      self.hovered_menu = i
      return
    end
  end
end


function TitleView:draw()
  self:draw_background(style.background2)
  self:draw_window_title()
  self:draw_window_controls()
  self.menu_context:draw()
end

return TitleView

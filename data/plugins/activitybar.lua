-- mod-version:3
local core = require "core"
local style = require "core.style"
local View = require "core.view"
local common = require "core.common"
local command = require "core.command"

local ActivityBar = View:extend()

function ActivityBar:new()
  ActivityBar.super.new(self)
  self.size.x = 50 * SCALE
  self.items = {
    { icon = "D", command = "treeview:toggle", tooltip = "Explorer" },
    { icon = "L", command = "project-search:find", tooltip = "Search" },
    { icon = "B", command = "core:find-command", tooltip = "Command Palette" },
    { icon = "f", command = "core:new-doc", tooltip = "New Doc" },
    { icon = "S", command = "doc:save", tooltip = "Save" },
    { icon = "P", command = "core:open-user-module", tooltip = "Settings" },
  }
  self.hovered_item = nil
end

function ActivityBar:get_name()
  return "Activity Bar"
end

function ActivityBar:draw()
  self:draw_background(style.background3)
  
  local ox, oy = self:get_content_offset()
  local y = oy + style.padding.y
  local w = self.size.x
  local h = 50 * SCALE

  for i, item in ipairs(self.items) do
    local color = style.dim
    if item == self.hovered_item then
      color = style.text
      renderer.draw_rect(ox, y, w, h, style.line_highlight)
    end
    
    common.draw_text(style.icon_big_font, color, item.icon, "center", ox, y, w, h)
    
    y = y + h
  end
end

function ActivityBar:on_mouse_moved(px, py, ...)
  ActivityBar.super.on_mouse_moved(self, px, py, ...)
  self.hovered_item = nil
  
  local ox, oy = self:get_content_offset()
  local y = oy + style.padding.y
  local w = self.size.x
  local h = 50 * SCALE
  
  for i, item in ipairs(self.items) do
    if px >= ox and px < ox + w and py >= y and py < y + h then
      self.hovered_item = item
      break
    end
    y = y + h
  end
end

function ActivityBar:on_mouse_pressed(button, x, y, clicks)
  if ActivityBar.super.on_mouse_pressed(self, button, x, y, clicks) then
    return true
  end
  
  if self.hovered_item then
    command.perform(self.hovered_item.command)
    return true
  end
end

local view = ActivityBar()
local node = core.root_view:get_active_node()
view.node = node:split("left", view, {x = true}, true)

return ActivityBar

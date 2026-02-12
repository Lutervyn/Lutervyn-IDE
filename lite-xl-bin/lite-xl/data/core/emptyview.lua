local common = require "core.common"
local style = require "core.style"
local keymap = require "core.keymap"
local View = require "core.view"

---@class core.emptyview : core.view
---@field super core.view
local EmptyView = View:extend()

function EmptyView:__tostring() return "EmptyView" end

function EmptyView:get_name()
  return "Get Started"
end

function EmptyView:get_filename()
  return ""
end


local core = require "core"

local lines = {
  { fmt = "Press %s to run a command", cmd = "core:find-command" },
  { fmt = "Press %s to open a file from the project", cmd = "core:open-file" },
  { fmt = "Press %s to open a project folder", cmd = "core:open-project-folder" },
}

local function draw_text(x, y, color)
  -- Load Posterama font if not present (safe load)
  if not style.posterama_big_font then
    local font_path = DATADIR .. "/fonts/Posterama1984.ttf"
    local status, font = pcall(renderer.font.load, font_path, 32 * SCALE) -- Bigger for welcome screen
    if status then
      style.posterama_big_font = font
    else
      style.posterama_big_font = style.big_font -- Fallback
    end
  end

  local th = style.posterama_big_font:get_height()
  local dh = th + style.padding.y * 2
  local x1, y1 = x, y + ((dh - th) / #lines)
  local title = "Lutervyn IDE"
  
  -- Use white for title
  local title_color = { common.color "#ffffff" }
  local sep_color = { common.color "#666666" }

  x = renderer.draw_text(style.posterama_big_font, title, x1, y1, title_color)
  x = x + style.padding.x
  renderer.draw_rect(x, y, math.ceil(1 * SCALE), dh, sep_color)
  th = style.font:get_height()
  y = y + (dh - (th + style.padding.y) * #lines) / 2
  local w = 0
  for _, line in ipairs(lines) do
    local text = string.format(line.fmt, keymap.get_binding(line.cmd))
    w = math.max(w, renderer.draw_text(style.font, text, x + style.padding.x, y, color))
    y = y + th + style.padding.y
  end
  return w, dh
end

function EmptyView:draw()
  self:draw_background(style.background)
  local w, h = draw_text(0, 0, { 0, 0, 0, 0 })
  local x = self.position.x + math.max(style.padding.x, (self.size.x - w) / 2)
  local y = self.position.y + (self.size.y - h) / 2
  draw_text(x, y, style.dim)
end

return EmptyView

-- mod-version:3
local core = require "core"
local command = require "core.command"
local style = require "core.style"
local View = require "core.view"
local keymap = require "core.keymap"

local AiderView = View:extend()

function AiderView:new()
  AiderView.super.new(self)
  self.scrollable = true
  self.lines = {}
  self.input_text = ""
  self.proc = nil
  self:start_aider()
end

function AiderView:get_name()
  return "Aider AI"
end

function AiderView:start_aider()
  if self.proc then return end
  -- Start aider with --watch-files to automatically detect changes
  self.proc = process.start({"aider", "--watch-files", "--no-auto-commits"}, {
    env = system.get_environment()
  })
  
  core.add_thread(function()
    while self.proc and self.proc:running() do
      local data = self.proc:read_stdout(1024)
      if data and #data > 0 then
        self:add_output(data)
      end
      local err = self.proc:read_stderr(1024)
      if err and #err > 0 then
        self:add_output(err)
      end
      coroutine.yield(0.1)
    end
  end)
end

function AiderView:add_output(text)
  -- Simple line splitting
  for line in text:gmatch("([^\r\n]*)\r?\n?") do
    if #line > 0 then
      table.insert(self.lines, line)
    end
  end
  self.scroll.to.y = #self.lines * style.font:get_height()
  core.redraw = true
end

function AiderView:draw()
  self:draw_background(style.background)
  
  local lh = style.font:get_height()
  local x, y = self:get_content_offset()
  x = x + style.padding.x
  y = y + style.padding.y
  
  -- Draw output lines
  for _, line in ipairs(self.lines) do
    common.draw_text(style.font, style.text, line, "left", x, y, self.size.x, lh)
    y = y + lh
  end
  
  -- Draw input area at the bottom
  local input_h = lh + style.padding.y * 2
  local input_y = self.position.y + self.size.y - input_h
  renderer.draw_rect(self.position.x, input_y, self.size.x, input_h, style.line_highlight)
  common.draw_text(style.font, style.accent, "> " .. self.input_text, "left", x, input_y + style.padding.y, self.size.x, lh)
end

function AiderView:on_text_input(text)
  self.input_text = self.input_text .. text
  core.redraw = true
end

function AiderView:on_key_pressed(key)
  if key == "backspace" then
    self.input_text = self.input_text:sub(1, -2)
  elseif key == "return" then
    if self.proc then
      self.proc:write(self.input_text .. "\n")
      self:add_output("> " .. self.input_text)
      self.input_text = ""
    end
  end
  core.redraw = true
  return true
end

command.add(nil, {
  ["aider:open"] = function()
    local node = core.root_view:get_active_node_default()
    local view = AiderView()
    node:split("right", view, {x = true}, true)
  end
})

keymap.add { ["ctrl+alt+a"] = "aider:open" }

return AiderView

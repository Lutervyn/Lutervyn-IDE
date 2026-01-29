-- mod-version:3
local core = require "core"
local common = require "core.common"
local style = require "core.style"
local renderer = require "renderer"
local command = require "core.command"
local NagView = require "core.nagview"

-- iOS Dark Mode Palette - Refined
style.nagbar_dim = { common.color "#00000080" }       -- Darker dim for contrast
style.nagbar_bg = { common.color "#2c2c2e" }         -- Real iOS Dark Modal Gray
style.nagbar_text = { common.color "#ffffff" }
style.nagbar_subtext = { common.color "#ebebf5" }     -- Brighter subtext
style.nagbar_divider = { common.color "#54545899" }   -- Separators
style.nagbar_action = { common.color "#0a84ff" }      -- Vivid Blue
style.nagbar_destructive = { common.color "#ff453a" } -- Vivid Red

-- Helper to draw rounded rect (stable version)
local function draw_rounded_rect(x, y, w, h, radius, color)
  -- Center body
  renderer.draw_rect(x, y + radius, w, h - 2 * radius, color)
  
  -- Caps (simple scanlines)
  for i = 0, radius - 1 do
    local d = radius - i - 1
    local w_slice = math.floor(math.sqrt(radius * radius - d * d) + 0.5)
    local x_start = x + radius - w_slice
    local width = w - 2 * radius + 2 * w_slice
    
    renderer.draw_rect(x_start, y + i, width, 1, color)
    renderer.draw_rect(x_start, y + h - i - 1, width, 1, color)
  end
end

local function draw_rounded_box(x, y, w, h, r, color)
  draw_rounded_rect(x, y, w, h, r, color)
end

-- Helper to wrap text to a max width
local function wrap_text(text, font, max_width)
  local lines = {}
  for line in text:gmatch("([^\n]*)\n?") do
    if line == "" then
       table.insert(lines, "")
    else
       local current_line = ""
       for word in line:gmatch("([^%s]+)") do
          local test_line = current_line == "" and word or (current_line .. " " .. word)
          if font:get_width(test_line) <= max_width then
             current_line = test_line
          else
             if current_line ~= "" then
                table.insert(lines, current_line)
                current_line = word
             else
                table.insert(lines, word)
                current_line = ""
             end
          end
       end
       if current_line ~= "" then
          table.insert(lines, current_line)
       end
    end
  end
  return lines
end

local function draw_centered_popup(self)
  local w, h = core.root_view.size.x, core.root_view.size.y
  
  -- Animation State
  if not self.anim_progress then self.anim_progress = 0 end
  self.anim_progress = common.lerp(self.anim_progress, 1, 0.25)
  if math.abs(1 - self.anim_progress) < 0.01 then self.anim_progress = 1 end
  
  -- Dim background
  local dim_col = { table.unpack(style.nagbar_dim) }
  dim_col[4] = dim_col[4] * self.anim_progress
  renderer.draw_rect(0, 0, w, h, dim_col)
  
  -- Dimensions
  local max_w = math.min(w * 0.85, 420 * SCALE) -- Wide enough for text
  local inner_padding = 24 * SCALE
  local text_max_w = max_w - (inner_padding * 2)
  
  local title_h = style.font:get_height() + inner_padding * 0.5
  
  local wrapped_message_lines = wrap_text(self.message, style.font, text_max_w)
  local msg_line_h = style.font:get_height() * 1.5
  local msg_h = (#wrapped_message_lines * msg_line_h) + inner_padding
  
  local btn_h = 48 * SCALE
  local popup_h = inner_padding + title_h + msg_h + btn_h
  local popup_w = max_w
  
  -- Pop Animation
  local scale = 0.95 + (0.05 * self.anim_progress)
  local cur_w = popup_w * scale
  local cur_h = popup_h * scale
  
  local x = math.floor((w - cur_w) / 2)
  local y = math.floor((h - cur_h) / 2)
  
  -- Background
  local radius = 14 * SCALE
  draw_rounded_box(x, y, cur_w, cur_h, radius, style.nagbar_bg)
  
  -- Title
  local ty = y + inner_padding
  common.draw_text(style.font, style.nagbar_text, self.title, "center", x, ty, cur_w, style.font:get_height())
  
  -- Message
  local my = ty + style.font:get_height() + inner_padding * 0.5
  for _, line in ipairs(wrapped_message_lines) do
    common.draw_text(style.font, style.nagbar_subtext, line, "center", x, my, cur_w, style.font:get_height())
    my = my + msg_line_h
  end
  
  -- Divider Line
  local div_y = y + cur_h - btn_h
  renderer.draw_rect(x, div_y, cur_w, 1, style.nagbar_divider)
  
  -- Buttons (Grid Layout)
  local count = #self.options
  local btn_w = cur_w / count
  
  for i, opt in ipairs(self.options) do
    local bx = x + (i-1) * btn_w
    
    -- Vertical Divider
    if i > 1 then
      renderer.draw_rect(bx, div_y, 1, btn_h, style.nagbar_divider)
    end
    
    -- Hover Highlight
    if i == self.hovered_item then
       -- Simple highlight (safe)
       renderer.draw_rect(bx, div_y + 1, btn_w, btn_h - 2, { common.color "#ffffff15" })
    end
    
    -- Text
    local txt_col = style.nagbar_action
    if opt.text == "No" or opt.text == "Delete" or opt.text == "Close Without Saving" then
       txt_col = style.nagbar_destructive
    end
    
    local label = opt.text
    if label == "Close Without Saving" then label = "Don't Save" end
    if label == "Save And Close" then label = "Save" end
    
    common.draw_text(style.font, txt_col, label, "center", bx, div_y + (btn_h - style.font:get_height())/2, btn_w, btn_h)
    
    -- Hit Rect logic (using final scale for simplicity)
    local final_btn_w = popup_w / count
    local final_div_y = math.floor((h - popup_h) / 2) + popup_h - btn_h
    local final_bx = math.floor((w - popup_w) / 2) + (i-1) * final_btn_w
    opt.rect = { x = final_bx, y = final_div_y, w = final_btn_w, h = btn_h }
  end
  
  if self.anim_progress < 1 then core.redraw = true end
end

-- Instance Override
core.add_thread(function()
  local nag = core.nag_view
  if not nag then return end
  
  nag.anim_progress = 0
  
  function nag:get_scrollable_size() return 0 end
  function nag:get_target_height() return 0 end

  function nag:draw()
    if not self.visible then 
      self.anim_progress = 0 
      return 
    end
    core.root_view:defer_draw(draw_centered_popup, self)
  end
  
  function nag:on_mouse_moved(mx, my, ...)
    if not self.visible then return end
    core.set_active_view(self)
    if self.options then
       for i, opt in ipairs(self.options) do
         if opt.rect then
           if mx >= opt.rect.x and my >= opt.rect.y and mx < opt.rect.x + opt.rect.w and my < opt.rect.y + opt.rect.h then
             self:change_hovered(i)
             break
           end
         end
       end
    end
  end

  function nag:on_mouse_pressed(button, mx, my, clicks)
    if not self.visible then return false end
    if self.options then
       for i, opt in ipairs(self.options) do
         if opt.rect then
           if mx >= opt.rect.x and my >= opt.rect.y and mx < opt.rect.x + opt.rect.w and my < opt.rect.y + opt.rect.h then
             self:change_hovered(i)
             command.perform "dialog:select"
             return true
           end
         end
       end
    end
    return true
  end
end)

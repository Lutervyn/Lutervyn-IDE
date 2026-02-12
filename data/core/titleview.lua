local core = require "core"
local common = require "core.common"
local command = require "core.command"
local style = require "core.style"
local View = require "core.view"
local ContextMenu = require "core.contextmenu"

-- ── Inline Terminal View ──────────────────────────────────────────────────
-- Defined here so clicking "Terminal" in the title bar always works,
-- even if the terminal plugin fails to load.
local TerminalView = View:extend()

-- Terminal colors
local terminal_colors = {
  output  = { common.color "#00e060ff" },  -- green  for shell output (prompts, etc)
  input   = { common.color "#42a5f5ff" },  -- blue   for user-typed input
  result  = { common.color "#ffffffee" },  -- white  for command result output
  header_bg    = { common.color "#252525ff" },  -- dark header background
  header_text  = { common.color "#ccccccff" },  -- header title text
  header_close = { common.color "#888888ff" },  -- close X default
  header_close_hover = { common.color "#ff5555ff" },  -- close X on hover
  header_border = { common.color "#444444ff" }, -- bottom border
}

function TerminalView:new()
  TerminalView.super.new(self)
  self.scrollable  = true
  self.cursor      = "ibeam"
  self.context     = "session"
  self.lines       = { "" }
  self.line_colors = { "output" }  -- color tag per line
  self.input       = ""
  self.prompt_len  = 0             -- length of the prompt text on current input line
  self.waiting_result = false      -- true after submit, until next prompt
  self.history     = {}
  self.history_idx = 0
  self.proc        = nil
  self.running     = false
  self.target_size = 250
  self.init_size   = true
  -- selection state
  self.sel_start_line = nil
  self.sel_start_col  = nil
  self.sel_end_line   = nil
  self.sel_end_col    = nil
  self.selecting      = false
  -- undo/redo for input
  self.undo_stack = {}
  self.redo_stack = {}
  -- header bar
  self.header_height = 28
  self.close_hovered = false
  self:start_shell()
end

function TerminalView:get_name() return "Terminal" end

-- Returns x, y, w, h of the close button in the header
function TerminalView:get_close_button_rect()
  local bsize = self.header_height - 8
  local bx = self.position.x + self.size.x - bsize - 8
  local by = self.position.y + 4
  return bx, by, bsize, bsize
end

-- Close this terminal panel
function TerminalView:close_terminal()
  if self.proc and self.running then
    pcall(function() self.proc:kill() end)
    self.running = false
    self.proc = nil
  end
  local root = core.root_view
  if root and root.root_node then
    local tnode, tview = nil, nil
    -- find our node
    local function find(node)
      if not node then return end
      if node.type == "leaf" then
        for _, v in ipairs(node.views) do
          if v == self then tnode = node; tview = v; return end
        end
      else
        find(node.a); find(node.b)
      end
    end
    find(root.root_node)
    if tnode and tview then
      tnode:close_view(root.root_node, tview)
    end
  end
end

function TerminalView:set_target_size(axis, value)
  if axis == "y" then
    self.target_size = value
    return true
  end
end

function TerminalView:start_shell()
  if not process then
    self:push_output("Error: 'process' module not available.\r\n")
    return
  end
  if self.proc then pcall(function() self.proc:kill() end); self.proc = nil end

  local cmd = PLATFORM == "Windows" and { "cmd.exe" } or { "/bin/bash" }
  local opts = {
    stdin  = process.REDIRECT_PIPE,
    stdout = process.REDIRECT_PIPE,
    stderr = process.REDIRECT_STDOUT,
  }
  local ok, proc = pcall(process.start, cmd, opts)
  if not ok or not proc then
    self:push_output("Error: could not start shell: " .. tostring(proc) .. "\r\n")
    return
  end
  self.proc    = proc
  self.running = true

  core.add_thread(function()
    while self.running and self.proc do
      local chunk = self.proc:read_stdout(4096)
      if chunk and #chunk > 0 then
        self:push_output(chunk)
        core.redraw = true
      else
        if not self.proc:running() then
          self:push_output("\r\n[Process exited]\r\n")
          self.running = false
          core.redraw = true
          break
        end
      end
      coroutine.yield(0.03)
    end
  end)
end

function TerminalView:push_output(text)
  text = text:gsub("\27%[[%d;]*[a-zA-Z]", "")
  text = text:gsub("\27%].-\a", "")
  text = text:gsub("\27[%(%)][AB012]", "")
  -- after submit, command result output is "result" (white)
  -- prompt lines from the shell stay "output" (green)
  local color_tag = self.waiting_result and "result" or "output"
  for i = 1, #text do
    local c = text:sub(i, i)
    if c == "\n" then
      table.insert(self.lines, "")
      table.insert(self.line_colors, color_tag)
    elseif c == "\r" then
      -- ignore
    elseif c == "\b" then
      local cur = self.lines[#self.lines]
      if #cur > 0 then self.lines[#self.lines] = cur:sub(1, -2) end
    else
      self.lines[#self.lines] = self.lines[#self.lines] .. c
      self.line_colors[#self.lines] = color_tag
    end
  end
  -- detect prompt lines (ends with > or $) -> mark green, record prompt length
  local last = self.lines[#self.lines] or ""
  if last:match(">%s*$") or last:match("%$%s*$") then
    self.waiting_result = false
    self.line_colors[#self.lines] = "output"
    self.prompt_len = #last  -- remember where the prompt text ends
  end
  while #self.lines > 5000 do
    table.remove(self.lines, 1)
    table.remove(self.line_colors, 1)
  end
  self:scroll_to_bottom()
end

function TerminalView:scroll_to_bottom()
  local lh = self:get_line_height()
  local total_rows = self:count_visual_rows()
  local max = total_rows * lh - self.size.y + lh * 2
  if max < 0 then max = 0 end
  self.scroll.to.y = max
end

function TerminalView:save_undo()
  table.insert(self.undo_stack, self.input)
  if #self.undo_stack > 100 then table.remove(self.undo_stack, 1) end
  self.redo_stack = {}
end

function TerminalView:undo()
  if #self.undo_stack == 0 then return end
  table.insert(self.redo_stack, self.input)
  local prev = table.remove(self.undo_stack)
  self:set_input(prev)
end

function TerminalView:redo()
  if #self.redo_stack == 0 then return end
  table.insert(self.undo_stack, self.input)
  local next_input = table.remove(self.redo_stack)
  self:set_input(next_input)
end

-- Replace the current input text on the prompt line
function TerminalView:set_input(new_input)
  local cur = self.lines[#self.lines] or ""
  -- remove old input from end of line
  if #self.input > 0 and #cur >= #self.input then
    self.lines[#self.lines] = cur:sub(1, #cur - #self.input)
  end
  self.input = new_input
  self.lines[#self.lines] = self.lines[#self.lines] .. self.input
  core.redraw = true
end

function TerminalView:on_text_input(text)
  self:save_undo()
  self.input = self.input .. text
  self.lines[#self.lines] = self.lines[#self.lines] .. text
  -- don't change line_colors here; draw() will split prompt (green) vs input (blue)
  self:scroll_to_bottom()
  core.redraw = true
end

function TerminalView:submit()
  if self.proc and self.running then
    if #self.input > 0 then
      table.insert(self.history, self.input)
      self.history_idx = #self.history + 1
    end
    -- Mark current line as "prompt" so it stays green+blue in draw
    -- Store the split info: prompt_len chars green, rest blue
    self.line_colors[#self.lines] = "prompt_input"
    if not self.line_splits then self.line_splits = {} end
    local line_text = self.lines[#self.lines] or ""
    self.line_splits[#self.lines] = #line_text - #self.input
    self.proc:write(self.input .. "\n")
    self.input = ""
    self.prompt_len = 0
    self.waiting_result = true  -- next output will be white (result)
  end
end

function TerminalView:backspace()
  if #self.input > 0 then
    self:save_undo()
    self.input = self.input:sub(1, -2)
    local cur = self.lines[#self.lines]
    if #cur > 0 then self.lines[#self.lines] = cur:sub(1, -2) end
    core.redraw = true
  end
end

function TerminalView:history_up()
  if self.history_idx > 1 then self:replace_input(self.history_idx - 1) end
end

function TerminalView:history_down()
  if self.history_idx <= #self.history then self:replace_input(self.history_idx + 1) end
end

function TerminalView:replace_input(idx)
  local cur = self.lines[#self.lines]
  if #self.input > 0 and #cur >= #self.input then
    self.lines[#self.lines] = cur:sub(1, #cur - #self.input)
  end
  self.history_idx = idx
  self.input = self.history[idx] or ""
  self.lines[#self.lines] = self.lines[#self.lines] .. self.input
  core.redraw = true
end

function TerminalView:get_line_height()
  return math.floor(style.code_font:get_height() * 1.2)
end

-- Returns the available width for text in the terminal
function TerminalView:get_text_width()
  return math.max(100, self.size.x - style.padding.x * 2 - style.scrollbar_size)
end

-- Wrap a single line into visual rows that fit within max_w pixels
function TerminalView:wrap_line(text, font, max_w)
  if not text or #text == 0 then return { "" } end
  if font:get_width(text) <= max_w then return { text } end
  local rows = {}
  local start = 1
  while start <= #text do
    -- binary-ish search for how many chars fit
    local lo, hi = start, #text
    local best = start  -- at least 1 char per row
    while lo <= hi do
      local mid = math.floor((lo + hi) / 2)
      if font:get_width(text:sub(start, mid)) <= max_w then
        best = mid
        lo = mid + 1
      else
        hi = mid - 1
      end
    end
    -- ensure at least 1 char per row to avoid infinite loop
    if best < start then best = start end
    table.insert(rows, text:sub(start, best))
    start = best + 1
  end
  return rows
end

-- Count total visual rows for all lines (for scrollbar)
function TerminalView:count_visual_rows()
  local font  = style.code_font
  local max_w = self:get_text_width()
  local total = 0
  for i = 1, #self.lines do
    local text = self.lines[i] or ""
    if #text == 0 or font:get_width(text) <= max_w then
      total = total + 1
    else
      total = total + #self:wrap_line(text, font, max_w)
    end
  end
  return total
end

function TerminalView:get_scrollable_size()
  local lh = self:get_line_height()
  return self:count_visual_rows() * lh + self.size.y - self.header_height
end

function TerminalView:update()
  -- manage our locked height
  local dest = self.target_size or 250
  if self.init_size then
    self.size.y = dest
    self.init_size = false
  else
    self:move_towards(self.size, "y", dest, nil, "terminal")
  end
  TerminalView.super.update(self)
end

function TerminalView:draw()
  self:draw_background(style.background)

  local font  = style.code_font
  local lh    = self:get_line_height()
  local hh    = self.header_height

  -- ── draw header bar ──
  local hx, hy = self.position.x, self.position.y
  local hw     = self.size.x
  renderer.draw_rect(hx, hy, hw, hh, terminal_colors.header_bg)
  -- bottom border
  renderer.draw_rect(hx, hy + hh - 1, hw, 1, terminal_colors.header_border)
  -- title text
  local title_font = style.font
  local title = "Terminal"
  local ty = hy + math.floor((hh - title_font:get_height()) / 2)
  renderer.draw_text(title_font, title, hx + 10, ty, terminal_colors.header_text)
  -- close button (X)
  local bx, by, bw, bh = self:get_close_button_rect()
  local close_color = self.close_hovered and terminal_colors.header_close_hover or terminal_colors.header_close
  if self.close_hovered then
    renderer.draw_rect(bx - 2, by - 2, bw + 4, bh + 4, { 255, 255, 255, 20 })
  end
  local xfont = style.icon_font or style.font
  local x_text = "X"
  local x_tw = xfont:get_width(x_text)
  local x_th = xfont:get_height()
  renderer.draw_text(xfont, x_text,
    bx + math.floor((bw - x_tw) / 2),
    by + math.floor((bh - x_th) / 2),
    close_color)

  -- ── draw terminal content below header ──
  local ox, oy = self:get_content_offset()
  oy = oy + hh  -- shift content below header
  local x     = ox + style.padding.x
  local max_w = self:get_text_width()
  local content_top    = self.position.y + hh
  local content_bottom = self.position.y + self.size.y
  local input_line_idx = #self.lines

  -- build visual rows: { text, color, line_idx, is_last_row_of_line }
  local rows = {}
  for i = 1, #self.lines do
    local line_text = self.lines[i] or ""
    local tag = self.line_colors[i] or "output"
    local wrapped = self:wrap_line(line_text, font, max_w)
    for ri, row_text in ipairs(wrapped) do
      table.insert(rows, {
        text = row_text,
        tag  = tag,
        line = i,
        is_last = (ri == #wrapped),
        char_offset = 0,  -- filled below
      })
    end
    -- compute char_offset for each wrapped row of this line
    local offset = 0
    local base = #rows - #wrapped + 1
    for ri = 1, #wrapped do
      rows[base + ri - 1].char_offset = offset
      offset = offset + #wrapped[ri]
    end
  end

  local total_rows = #rows
  local first_row = math.max(1, math.floor(self.scroll.y / lh))
  local last_row  = math.min(total_rows, first_row + math.ceil(self.size.y / lh) + 1)

  -- draw text rows
  for r = first_row, last_row do
    local ly = oy + (r - 1) * lh
    if ly + lh >= content_top and ly <= content_bottom then
      local row = rows[r]
      local rt  = row.text
      local tag = row.tag
      local li  = row.line

      -- active input line: split prompt (green) + input (blue)
      if li == input_line_idx and #self.input > 0 then
        local full_line = self.lines[li] or ""
        local prompt_chars = #full_line - #self.input
        local co = row.char_offset
        local row_end = co + #rt
        if co >= prompt_chars then
          -- entire row is input text
          renderer.draw_text(font, rt, x, ly, terminal_colors.input)
        elseif row_end <= prompt_chars then
          -- entire row is prompt text
          renderer.draw_text(font, rt, x, ly, terminal_colors.output)
        else
          -- row contains both prompt and input
          local split = prompt_chars - co
          local prompt_part = rt:sub(1, split)
          local input_part  = rt:sub(split + 1)
          local pw = renderer.draw_text(font, prompt_part, x, ly, terminal_colors.output)
          renderer.draw_text(font, input_part, pw, ly, terminal_colors.input)
        end
      -- past submitted lines: prompt green + command blue
      elseif tag == "prompt_input" and self.line_splits and self.line_splits[li] then
        local split_at = self.line_splits[li]
        local co = row.char_offset
        local row_end = co + #rt
        if co >= split_at then
          renderer.draw_text(font, rt, x, ly, terminal_colors.input)
        elseif row_end <= split_at then
          renderer.draw_text(font, rt, x, ly, terminal_colors.output)
        else
          local split = split_at - co
          local prompt_part = rt:sub(1, split)
          local input_part  = rt:sub(split + 1)
          local pw = renderer.draw_text(font, prompt_part, x, ly, terminal_colors.output)
          renderer.draw_text(font, input_part, pw, ly, terminal_colors.input)
        end
      else
        local color = terminal_colors[tag] or terminal_colors.output
        renderer.draw_text(font, rt, x, ly, color)
      end
    end
  end

  -- draw selection highlight (simplified - based on visual rows)
  local sl, sc, el, ec = self:get_selection_range()
  if sl then
    local sel_color = { 80, 130, 220, 80 }
    for r = first_row, last_row do
      local ly = oy + (r - 1) * lh
      if ly + lh >= content_top and ly <= content_bottom then
        local row = rows[r]
        local li  = row.line
        local co  = row.char_offset
        local rt  = row.text
        -- check if this row's line is in selection range
        if li >= sl and li <= el then
          local row_start_col = co
          local row_end_col   = co + #rt
          local sel_start_in_line = (li == sl) and sc or 0
          local sel_end_in_line   = (li == el) and ec or #(self.lines[li] or "")
          -- clamp to this row's range
          local s = math.max(sel_start_in_line, row_start_col)
          local e = math.min(sel_end_in_line, row_end_col)
          if e > s then
            local sx1 = x + font:get_width(rt:sub(1, s - co))
            local sx2 = x + font:get_width(rt:sub(1, e - co))
            renderer.draw_rect(sx1, ly, sx2 - sx1, lh, sel_color)
          end
        end
      end
    end
  end

  -- blinking cursor (on the last visual row)
  if core.active_view == self and total_rows > 0 then
    local last_r = rows[total_rows]
    local cursor_text = last_r and last_r.text or ""
    local cursor_x = x + font:get_width(cursor_text)
    local cursor_y = oy + (total_rows - 1) * lh
    if cursor_y + lh >= content_top and cursor_y <= content_bottom then
      local t = system.get_time()
      if math.floor(t * 2) % 2 == 0 then
        renderer.draw_rect(cursor_x, cursor_y, style.caret_width, lh, style.caret)
      end
      core.redraw = true
    end
  end
  self:draw_scrollbar()
end

-- Convert mouse x,y to line number and character column
function TerminalView:mouse_to_pos(mx, my)
  local font = style.code_font
  local lh   = self:get_line_height()
  local ox, oy = self:get_content_offset()
  oy = oy + self.header_height
  local x0   = ox + style.padding.x

  local line = math.floor((my - oy) / lh) + 1
  line = math.max(1, math.min(line, #self.lines))

  local text = self.lines[line] or ""
  local col = 0
  for c = 1, #text do
    local w = font:get_width(text:sub(1, c))
    if x0 + w > mx then break end
    col = c
  end
  return line, col
end

function TerminalView:clear_selection()
  self.sel_start_line = nil
  self.sel_start_col  = nil
  self.sel_end_line   = nil
  self.sel_end_col    = nil
  self.selecting      = false
end

function TerminalView:has_selection()
  return self.sel_start_line and self.sel_end_line
    and (self.sel_start_line ~= self.sel_end_line or self.sel_start_col ~= self.sel_end_col)
end

-- Get normalized selection (start before end)
function TerminalView:get_selection_range()
  if not self:has_selection() then return nil end
  local sl, sc, el, ec = self.sel_start_line, self.sel_start_col,
                          self.sel_end_line,   self.sel_end_col
  if sl > el or (sl == el and sc > ec) then
    sl, sc, el, ec = el, ec, sl, sc
  end
  return sl, sc, el, ec
end

function TerminalView:get_selected_text()
  local sl, sc, el, ec = self:get_selection_range()
  if not sl then return "" end
  if sl == el then
    return (self.lines[sl] or ""):sub(sc + 1, ec)
  end
  local parts = {}
  table.insert(parts, (self.lines[sl] or ""):sub(sc + 1))
  for i = sl + 1, el - 1 do
    table.insert(parts, self.lines[i] or "")
  end
  table.insert(parts, (self.lines[el] or ""):sub(1, ec))
  return table.concat(parts, "\n")
end

function TerminalView:on_mouse_pressed(button, mx, my, clicks)
  -- check close button click
  if button == "left" then
    local bx, by, bw, bh = self:get_close_button_rect()
    if mx >= bx and mx <= bx + bw and my >= by and my <= by + bh then
      self:close_terminal()
      return true
    end
  end
  -- ignore clicks on the header bar (don't start selection there)
  if my < self.position.y + self.header_height then
    return true
  end
  if TerminalView.super.on_mouse_pressed then
    local r = TerminalView.super.on_mouse_pressed(self, button, mx, my, clicks)
    if r then return r end
  end
  if button == "left" then
    local line, col = self:mouse_to_pos(mx, my)
    self.sel_start_line = line
    self.sel_start_col  = col
    self.sel_end_line   = line
    self.sel_end_col    = col
    self.selecting      = true
    core.redraw = true
  end
  return true
end

function TerminalView:on_mouse_moved(mx, my, ...)
  if TerminalView.super.on_mouse_moved then
    TerminalView.super.on_mouse_moved(self, mx, my, ...)
  end
  -- track close button hover
  local bx, by, bw, bh = self:get_close_button_rect()
  local was_hovered = self.close_hovered
  self.close_hovered = mx >= bx and mx <= bx + bw and my >= by and my <= by + bh
  if was_hovered ~= self.close_hovered then core.redraw = true end
  -- update cursor style
  if self.close_hovered then
    self.cursor = "arrow"
  elseif my < self.position.y + self.header_height then
    self.cursor = "arrow"
  else
    self.cursor = "ibeam"
  end
  if self.selecting then
    local line, col = self:mouse_to_pos(mx, my)
    self.sel_end_line = line
    self.sel_end_col  = col
    core.redraw = true
  end
  return true
end

function TerminalView:on_mouse_released(button, mx, my)
  if button == "left" then
    self.selecting = false
  end
end

function TerminalView:copy_selection()
  local text = self:get_selected_text()
  if #text > 0 then
    system.set_clipboard(text)
    core.log("Copied to clipboard")
  end
end

function TerminalView:paste_clipboard()
  local text = system.get_clipboard()
  if text and #text > 0 then
    -- strip \r\n to just text, send to input
    text = text:gsub("\r\n", "\n"):gsub("\r", "\n")
    -- only take first line for safety
    local first_line = text:match("^([^\n]*)")
    if first_line and #first_line > 0 then
      self.input = self.input .. first_line
      self.lines[#self.lines] = self.lines[#self.lines] .. first_line
      self:scroll_to_bottom()
      core.redraw = true
    end
  end
end

function TerminalView:on_mouse_wheel(ywheel)
  local lh = self:get_line_height()
  self.scroll.to.y = self.scroll.to.y - ywheel * lh * 3
  return true
end

-- Find existing terminal in the node tree
local function find_terminal_in_tree(node)
  if not node then return nil, nil end
  if node.type == "leaf" then
    for _, v in ipairs(node.views) do
      if v:is(TerminalView) then return node, v end
    end
  else
    local n, v = find_terminal_in_tree(node.a)
    if v then return n, v end
    return find_terminal_in_tree(node.b)
  end
end

-- Register terminal commands and keybindings
local function is_terminal_view()
  return core.active_view and core.active_view:is(TerminalView)
end

local terminal_commands_registered = false
local register_terminal_commands  -- forward declaration
local toggle_terminal              -- forward declaration

-- Toggle terminal panel
toggle_terminal = function()
  register_terminal_commands()

  local root = core.root_view
  if not root or not root.root_node then
    core.log("Terminal: root_view or root_node is nil")
    return
  end

  local tnode, tview = find_terminal_in_tree(root.root_node)
  if tview then
    if core.active_view == tview then
      tnode:close_view(root.root_node, tview)
    else
      tnode:set_active_view(tview)
      core.set_active_view(tview)
    end
    return
  end

  local primary = root:get_primary_node()
  if not primary then
    core.log("Terminal: get_primary_node returned nil")
    return
  end

  core.log("Terminal: creating new TerminalView...")
  local ok, err = pcall(function()
    local tv = TerminalView()
    core.log("Terminal: TerminalView created, splitting...")
    local new_node = primary:split("down", tv, { y = true }, true)
    core.log("Terminal: split done, setting active view...")
    core.set_active_view(tv)
    core.log("Terminal: DONE - terminal should be visible now")
  end)
  if not ok then
    core.log("Terminal: ERROR creating terminal: %s", tostring(err))
  end
end

register_terminal_commands = function()
  if terminal_commands_registered then return end
  terminal_commands_registered = true

  local keymap = require "core.keymap"

  command.add(is_terminal_view, {
    ["terminal:submit"] = function() core.active_view:submit() end,
    ["terminal:backspace"] = function() core.active_view:backspace() end,
    ["terminal:history-up"] = function() core.active_view:history_up() end,
    ["terminal:history-down"] = function() core.active_view:history_down() end,
    ["terminal:copy"] = function()
      local tv = core.active_view
      if tv:has_selection() then
        tv:copy_selection()
        tv:clear_selection()
      elseif tv.proc and tv.running then
        -- no selection: send Ctrl+C to the process
        tv.proc:write("\3")
      end
    end,
    ["terminal:paste"] = function() core.active_view:paste_clipboard() end,
    ["terminal:undo"] = function() core.active_view:undo() end,
    ["terminal:redo"] = function() core.active_view:redo() end,
    ["terminal:select-all"] = function()
      local tv = core.active_view
      tv.sel_start_line = 1
      tv.sel_start_col  = 0
      tv.sel_end_line   = #tv.lines
      tv.sel_end_col    = #(tv.lines[#tv.lines] or "")
      core.redraw = true
    end,
  })

  command.add(nil, {
    ["terminal:toggle"] = toggle_terminal,
  })

  keymap.add {
    ["return"]    = "terminal:submit",
    ["backspace"] = "terminal:backspace",
    ["up"]        = "terminal:history-up",
    ["down"]      = "terminal:history-down",
    ["ctrl+`"]    = "terminal:toggle",
    ["ctrl+c"]    = "terminal:copy",
    ["ctrl+v"]    = "terminal:paste",
    ["ctrl+z"]    = "terminal:undo",
    ["ctrl+y"]    = "terminal:redo",
    ["ctrl+a"]    = "terminal:select-all",
  }
end

local icon_colors = {
  bg = { common.color "#1a1a1aff" },
  text = { common.color "#ffffffff" },
  dim = { common.color "#999999ff" },
  silver = { common.color "#ccccccff" }
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
      { text = "New File", command = "core:new-doc", info = "Ctrl+N" },
      { text = "New Window", command = "core:restart" }, 
      ContextMenu.DIVIDER,
      { text = "Open File...", command = "core:open-file", info = "Ctrl+O" },
      { text = "Open Folder...", command = "core:open-project-folder" },
      ContextMenu.DIVIDER,
      { text = "Save", command = "doc:save", info = "Ctrl+S" },
      { text = "Save As...", command = "doc:save-as", info = "Ctrl+Shift+S" },
      ContextMenu.DIVIDER,
      { text = "Exit", command = "core:quit" },
    }},
    { text = "Edit", items = {
      { text = "Undo", command = "doc:undo", info = "Ctrl+Z" },
      { text = "Redo", command = "doc:redo", info = "Ctrl+Y" },
      ContextMenu.DIVIDER,
      { text = "Cut", command = "doc:cut", info = "Ctrl+X" },
      { text = "Copy", command = "doc:copy", info = "Ctrl+C" },
      { text = "Paste", command = "doc:paste", info = "Ctrl+V" },
      ContextMenu.DIVIDER,
      { text = "Find", command = "find-replace:find", info = "Ctrl+F" },
      { text = "Replace", command = "find-replace:replace", info = "Ctrl+H" },
    }},
    { text = "Selection", items = {
      { text = "Select All", command = "doc:select-all", info = "Ctrl+A" },
      { text = "Select Line", command = "doc:select-lines" },
      { text = "Select Word", command = "doc:select-word" },
      ContextMenu.DIVIDER,
      { text = "Duplicate Line", command = "doc:duplicate-lines", info = "Ctrl+Shift+D" },
      { text = "Move Line Up", command = "doc:move-lines-up", info = "Alt+Up" },
      { text = "Move Line Down", command = "doc:move-lines-down", info = "Alt+Down" },
    }},
    { text = "View", items = {
      { text = "Command Palette", command = "core:find-command", info = "Ctrl+Shift+P" },
      { text = "Toggle Sidebar", command = "treeview:toggle", info = "Ctrl+\\" },
      { text = "Toggle Log", command = "core:toggle-log" },
      ContextMenu.DIVIDER,
      { text = "Increase Font Size", command = "font:increase", info = "Ctrl++" },
      { text = "Decrease Font Size", command = "font:decrease", info = "Ctrl+-" },
    }},
    { text = "Go", items = {
      { text = "Go to File...", command = "core:find-file", info = "Ctrl+P" },
      { text = "Go to Line...", command = "doc:go-to-line", info = "Ctrl+G" },
      { text = "Go to Symbol...", command = "core:find-command" }, -- Approximation
    }},
    { text = "Run", items = {
      { text = "Run Command", command = "core:find-command" },
      -- Build plugins would add items here dynamically in a real scenario
    }},
    { text = "Terminal", action = toggle_terminal },
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
    system.set_window_hit_test(title_height, controls_width, icon_spacing)
    core.hit_test_title_height = title_height
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
  
  -- Dynamic hit test adjustment: Make menus clickable by excluding them from "caption" hit test
  if self.visible then 
     local logo_w = 0
     if style.logo_image then
       local orig_w = style.logo_image:get_width()
       local orig_h = style.logo_image:get_height()
       local target_h = math.floor(style.font:get_height())
       local scale = target_h / orig_h
       logo_w = math.floor(orig_w * scale) + style.padding.x * 2
     else
       local logo_text = "LUTERVYN </>"
       local draw_font = style.posterama_font or style.font
       logo_w = draw_font:get_width(logo_text) + style.padding.x * 2
     end
     
     -- "controls_width" is the width from the RIGHT edge that is treated as Client (Clickable)
     -- We want everything except the logo to be clickable.
     -- So controls_width = Window Width - Logo Width
     local win_width = self.size.x
     local controls_width = win_width - logo_w
     
     if controls_width < 0 then controls_width = 0 end
     
     local title_height = title_view_height()
     system.set_window_hit_test(title_height, controls_width, 0)
  end

  TitleView.super.update(self)
end


function TitleView:draw_window_title()
  local h = style.font:get_height()
  local ox, oy = self:get_content_offset()
  local x, y = ox + style.padding.x, oy + style.padding.y

  -- Load Logo Image (if not already loaded)
  -- Check if renderer.image API exists (requires recompilation)
  if renderer.image and not style.logo_image and not style.logo_failed then
    local icon_path = DATADIR .. "/icons/logo.png"
    local status, img = pcall(renderer.image.load, icon_path)
    if status then
      style.logo_image = img
    else
      core.log("Failed to load logo image: " .. tostring(img))
      style.logo_failed = true
    end
  end
  
  -- Draw "LUTERVYN" logo (Image or Text Fallback)
  if style.logo_image then
    local orig_w = style.logo_image:get_width()
    local orig_h = style.logo_image:get_height()
    
    -- Scale logo to fit the title bar height
    local target_h = math.floor(h)
    local scale = target_h / orig_h
    local target_w = math.floor(orig_w * scale)
    
    -- Center logo vertically in the title bar
    local img_y = y + (h - target_h) / 2
    renderer.draw_image(style.logo_image, x, img_y, target_w, target_h)
    x = x + target_w + style.padding.x
  else
    -- Fallback to text
    -- Load Posterama font for logo (if not already loaded)
    if not style.posterama_font then
      local font_path = DATADIR .. "/fonts/Posterama1984.ttf"
      local status, font = pcall(renderer.font.load, font_path, 16 * SCALE)
      if status then
        style.posterama_font = font
      else
        if not style.posterama_failed then 
          core.log("Failed to load posterama font (using fallback): " .. tostring(font))
          style.posterama_failed = true
        end
        style.posterama_font = style.font -- Fallback
      end
    end
    
    local logo_text = "LUTERVYN </>"
    local draw_font = style.posterama_font or style.font
    local logo_w = draw_font:get_width(logo_text)
    common.draw_text(draw_font, icon_colors.text, logo_text, nil, x, y, 0, h)
    x = x + logo_w + style.padding.x
  end
  
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
  local ox, oy = self:get_content_offset()
  for item, x, y, w, h in self:each_control_item() do
    local hovered = item == self.hovered_item
    local icon_color = hovered and style.text or style.dim
    local bg_color = hovered and style.dim or nil
    
    if item.symbol == "X" and hovered then
      bg_color = { common.color "#cc0000" } -- Red background for close on hover
      icon_color = style.text
    end
    
    -- Draw button background on hover
    if bg_color then
      renderer.draw_rect(x, y, w, h, bg_color)
    end
    
    -- Center icons within the button area
    local cx, cy = x + w / 2, y + h / 2
    local size = common.round(10 * SCALE)
    local half = size / 2
    
    if item.symbol == "_" then -- Minimize
      renderer.draw_rect(cx - half, cy, size, 1 * SCALE, icon_color)
      
    elseif item.symbol == "W" then -- Maximize
      renderer.draw_rect(cx - half, cy - half, size, size, icon_color) -- Outer border
      renderer.draw_rect(cx - half + 1*SCALE, cy - half + 1*SCALE, size - 2*SCALE, size - 2*SCALE, bg_color or style.background2) -- Inner fill (hollow)
      
    elseif item.symbol == "w" then -- Restore
      -- Two overlapping rectangles
      local offset = 2 * SCALE
      local s2 = size - offset
      -- Back rect
      renderer.draw_rect(cx - half + offset, cy - half - offset, s2, s2, icon_color)
      -- Front rect (fill to cover back)
      renderer.draw_rect(cx - half, cy - half, s2, s2, bg_color or style.background2) -- Fill
      renderer.draw_rect(cx - half, cy - half, s2, s2, icon_color) -- Border
      renderer.draw_rect(cx - half + 1*SCALE, cy - half + 1*SCALE, s2 - 2*SCALE, s2 - 2*SCALE, bg_color or style.background2) -- Inner
      
    elseif item.symbol == "X" then -- Close
      common.draw_text(style.icon_font, icon_color, "X", nil, cx - style.icon_font:get_width("X")/2, cy - style.icon_font:get_height()/2, 0, h)
    end
  end
end


function TitleView:on_mouse_pressed(button, x, y, clicks)
  core.log("TitleView:on_mouse_pressed called at x=%d y=%d hovered=%s", x, y, tostring(self.hovered_menu))
  if self.menu_context:on_mouse_pressed(button, x, y, clicks) then return true end
  
  -- Handle menu opening on left click before window dragging (super)
  if self.hovered_menu and button == "left" then
    local menu_idx = self.hovered_menu
    local menu = self.menu_items[menu_idx]
    local rect = self.menu_rects[menu_idx]
    if menu and rect then
      -- Direct action button (no dropdown)
      if menu.action then
        if type(menu.action) == "function" then
          core.log("Terminal button clicked - calling toggle")
          menu.action()
        elseif type(menu.action) == "string" then
          command.perform(menu.action)
        end
        return true
      end
      -- Dropdown menu
      if menu.items then
        -- Build item list directly (bypass command.is_valid filtering)
        local items_list = { width = 0, height = 0 }
        for _, item in ipairs(rect.items) do
          local lw, lh
          if item == ContextMenu.DIVIDER then
            lw = 0
            lh = 1 + 5 * SCALE * 2
          else
            lw = style.font:get_width(item.text)
            if item.info then
              lw = lw + style.padding.x + style.font:get_width(item.info)
            end
            lh = style.font:get_height() + style.padding.y
          end
          items_list.width = math.max(items_list.width, lw)
          items_list.height = items_list.height + lh
          table.insert(items_list, item)
        end
        items_list.width = items_list.width + style.padding.x * 2
        
        if #items_list > 0 then
          self.menu_context.items = items_list
          local show_x = common.clamp(rect.x, 0, core.root_view.size.x - items_list.width - style.padding.x)
          local show_y = common.clamp(rect.y + rect.h + style.padding.y, 0, core.root_view.size.y - items_list.height)
          self.menu_context.position.x = show_x
          self.menu_context.position.y = show_y
          self.menu_context.show_context_menu = true
          core.request_cursor("arrow")
        end
        return true
      end
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

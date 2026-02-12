-- mod-version:3
local core = require "core"
local config = require "core.config"
local common = require "core.common"
local command = require "core.command"

config.plugins.autosave = common.merge({
  enabled = true,
  interval = 60, -- Save all every 60 seconds
  idle_timeout = 1, -- Save current if idle for 1 second (VS Code default 'afterDelay')
}, config.plugins.autosave)

local last_active = true
local last_save_time = system.get_time()
local last_change_time = system.get_time()
local active_doc = nil

-- Patch Doc:insert and Doc:remove to track changes
local Doc = require "core.doc"
local old_insert = Doc.insert
local old_remove = Doc.remove

function Doc:insert(...)
  old_insert(self, ...)
  if self == active_doc then
    last_change_time = system.get_time()
  end
end

function Doc:remove(...)
  old_remove(self, ...)
  if self == active_doc then
    last_change_time = system.get_time()
  end
end

local function save_all_dirty()
  local saved_count = 0
  for _, doc in ipairs(core.docs) do
    if doc:is_dirty() and doc.filename then
      doc:save()
      saved_count = saved_count + 1
    end
  end
  if saved_count > 0 then
    core.log_quiet("Auto-saved %d files", saved_count)
  end
end

core.add_thread(function()
  while true do
    if config.plugins.autosave.enabled then
      local now = system.get_time()
      local is_active = system.window_has_focus()
      
      -- Update active doc reference for the patch
      local dv = core.active_view
      active_doc = (dv and dv:is(require("core.docview"))) and dv.doc or nil
      
      -- 1. Focus Lost Trigger
      if last_active and not is_active then
        save_all_dirty()
      end
      last_active = is_active
      
      -- 2. Periodic Interval Trigger
      if now - last_save_time >= config.plugins.autosave.interval then
        save_all_dirty()
        last_save_time = now
      end
      
      -- 3. Immediate Idle Trigger (VS Code Style)
      if active_doc and active_doc:is_dirty() and active_doc.filename then
        if now - last_change_time >= config.plugins.autosave.idle_timeout then
          active_doc:save()
          last_change_time = now -- Reset to avoid multiple saves for same idle
          core.log_quiet("Auto-saved: %s", active_doc.filename)
        end
      end
    end
    
    coroutine.yield(0.1) -- Check more frequently for "immediate" feel
  end
end)

command.add(nil, {
  ["autosave:toggle"] = function()
    config.plugins.autosave.enabled = not config.plugins.autosave.enabled
    core.log("Auto Save: %s", config.plugins.autosave.enabled and "Enabled" or "Disabled")
  end
})

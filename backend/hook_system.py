"""Event-driven hook system for plugin architecture.

Copyright (C) 2025 Kasa Monitor Contributors

This file is part of Kasa Monitor.

Kasa Monitor is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Kasa Monitor is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Kasa Monitor. If not, see <https://www.gnu.org/licenses/>.
"""

import asyncio
import inspect
import sqlite3
import json
import time
import threading
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable, Union, Awaitable
from enum import Enum
from dataclasses import dataclass, asdict
from collections import defaultdict
import queue
import weakref


class HookType(Enum):
    """Hook types."""

    PRE = "pre"
    POST = "post"
    FILTER = "filter"
    ACTION = "action"
    EVENT = "event"


class HookPriority(Enum):
    """Hook execution priority."""

    FIRST = -100
    HIGH = -10
    NORMAL = 0
    LOW = 10
    LAST = 100


class EventPriority(Enum):
    """Event priority levels."""

    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


@dataclass
class Hook:
    """Hook definition."""

    name: str
    callback: Callable
    plugin_id: Optional[str] = None
    hook_type: HookType = HookType.ACTION
    priority: HookPriority = HookPriority.NORMAL
    conditions: Optional[Dict] = None
    async_hook: bool = False
    enabled: bool = True
    metadata: Optional[Dict] = None

    def __hash__(self):
        """Make hook hashable."""
        return hash((self.name, self.plugin_id, id(self.callback)))

    def __eq__(self, other):
        """Check hook equality."""
        if not isinstance(other, Hook):
            return False
        return (
            self.name == other.name
            and self.plugin_id == other.plugin_id
            and self.callback == other.callback
        )


@dataclass
class Event:
    """Event definition."""

    name: str
    data: Any
    source: Optional[str] = None
    timestamp: Optional[datetime] = None
    priority: EventPriority = EventPriority.NORMAL
    metadata: Optional[Dict] = None

    def __post_init__(self):
        """Initialize timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.now()

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "data": self.data,
            "source": self.source,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "priority": self.priority.value,
            "metadata": self.metadata,
        }


@dataclass
class HookResult:
    """Hook execution result."""

    hook_name: str
    plugin_id: Optional[str]
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


class HookRegistry:
    """Central hook registry."""

    def __init__(self, db_path: str = "kasa_monitor.db"):
        """Initialize hook registry.

        Args:
            db_path: Path to database
        """
        self.db_path = db_path
        self.hooks = defaultdict(list)
        self.hook_cache = {}
        self.conditions_cache = {}
        self._lock = threading.RLock()

        self._init_database()

    def _init_database(self):
        """Initialize hook tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Hook definitions table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS hook_definitions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                plugin_id TEXT,
                hook_type TEXT NOT NULL,
                priority INTEGER DEFAULT 0,
                conditions TEXT,
                async_hook BOOLEAN DEFAULT 0,
                enabled BOOLEAN DEFAULT 1,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(name, plugin_id)
            )
        """
        )

        # Hook execution history
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS hook_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hook_name TEXT NOT NULL,
                plugin_id TEXT,
                triggered_at TIMESTAMP NOT NULL,
                execution_time REAL,
                success BOOLEAN,
                error_message TEXT,
                input_data TEXT,
                output_data TEXT
            )
        """
        )

        # Create indexes
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_hook_name ON hook_definitions(name)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_hook_plugin ON hook_definitions(plugin_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_hook_exec_name ON hook_executions(hook_name)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_hook_exec_time ON hook_executions(triggered_at)"
        )

        conn.commit()
        conn.close()

    def register(self, hook: Hook) -> bool:
        """Register a hook.

        Args:
            hook: Hook to register

        Returns:
            True if registered successfully
        """
        with self._lock:
            # Check if callback is async
            if asyncio.iscoroutinefunction(hook.callback):
                hook.async_hook = True

            # Add to registry
            self.hooks[hook.name].append(hook)

            # Sort by priority
            self.hooks[hook.name].sort(key=lambda h: h.priority.value)

            # Clear cache
            self._clear_cache(hook.name)

            # Store in database
            self._store_hook_definition(hook)

            return True

    def unregister(
        self,
        hook_name: str,
        plugin_id: Optional[str] = None,
        callback: Optional[Callable] = None,
    ) -> bool:
        """Unregister a hook.

        Args:
            hook_name: Hook name
            plugin_id: Plugin ID (optional)
            callback: Specific callback (optional)

        Returns:
            True if unregistered successfully
        """
        with self._lock:
            if hook_name not in self.hooks:
                return False

            # Filter hooks
            remaining = []
            removed = False

            for hook in self.hooks[hook_name]:
                should_remove = True

                if plugin_id and hook.plugin_id != plugin_id:
                    should_remove = False
                if callback and hook.callback != callback:
                    should_remove = False

                if not should_remove:
                    remaining.append(hook)
                else:
                    removed = True

            if removed:
                if remaining:
                    self.hooks[hook_name] = remaining
                else:
                    del self.hooks[hook_name]

                # Clear cache
                self._clear_cache(hook_name)

                # Update database
                self._remove_hook_definition(hook_name, plugin_id)

            return removed

    def has_hook(self, hook_name: str) -> bool:
        """Check if hook exists.

        Args:
            hook_name: Hook name

        Returns:
            True if hook exists
        """
        with self._lock:
            return hook_name in self.hooks and len(self.hooks[hook_name]) > 0

    def get_hooks(self, hook_name: str) -> List[Hook]:
        """Get hooks by name.

        Args:
            hook_name: Hook name

        Returns:
            List of hooks
        """
        with self._lock:
            return self.hooks.get(hook_name, []).copy()

    def list_hooks(self, plugin_id: Optional[str] = None) -> List[str]:
        """List registered hook names.

        Args:
            plugin_id: Filter by plugin ID

        Returns:
            List of hook names
        """
        with self._lock:
            if plugin_id:
                hook_names = []
                for name, hooks in self.hooks.items():
                    if any(h.plugin_id == plugin_id for h in hooks):
                        hook_names.append(name)
                return hook_names
            else:
                return list(self.hooks.keys())

    def _store_hook_definition(self, hook: Hook):
        """Store hook definition in database.

        Args:
            hook: Hook to store
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO hook_definitions
            (name, plugin_id, hook_type, priority, conditions, async_hook,
             enabled, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                hook.name,
                hook.plugin_id,
                hook.hook_type.value,
                hook.priority.value,
                json.dumps(hook.conditions) if hook.conditions else None,
                hook.async_hook,
                hook.enabled,
                json.dumps(hook.metadata) if hook.metadata else None,
            ),
        )

        conn.commit()
        conn.close()

    def _remove_hook_definition(self, hook_name: str, plugin_id: Optional[str]):
        """Remove hook definition from database.

        Args:
            hook_name: Hook name
            plugin_id: Plugin ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if plugin_id:
            cursor.execute(
                "DELETE FROM hook_definitions WHERE name = ? AND plugin_id = ?",
                (hook_name, plugin_id),
            )
        else:
            cursor.execute("DELETE FROM hook_definitions WHERE name = ?", (hook_name,))

        conn.commit()
        conn.close()

    def _clear_cache(self, hook_name: str):
        """Clear hook cache.

        Args:
            hook_name: Hook name
        """
        if hook_name in self.hook_cache:
            del self.hook_cache[hook_name]
        if hook_name in self.conditions_cache:
            del self.conditions_cache[hook_name]


class HookExecutor:
    """Hook executor with async support."""

    def __init__(self, registry: HookRegistry):
        """Initialize hook executor.

        Args:
            registry: Hook registry
        """
        self.registry = registry
        self.running = False
        self.event_loop = None
        self.executor_thread = None

    async def execute(self, hook_name: str, *args, **kwargs) -> List[HookResult]:
        """Execute hooks by name.

        Args:
            hook_name: Hook name
            *args: Hook arguments
            **kwargs: Hook keyword arguments

        Returns:
            List of execution results
        """
        hooks = self.registry.get_hooks(hook_name)

        if not hooks:
            return []

        results = []

        for hook in hooks:
            if not hook.enabled:
                continue

            # Check conditions
            if hook.conditions and not self._check_conditions(
                hook.conditions, *args, **kwargs
            ):
                continue

            # Execute hook
            result = await self._execute_single(hook, *args, **kwargs)
            results.append(result)

            # Record execution
            self._record_execution(hook, result, args, kwargs)

            # For filter hooks, pass result to next hook
            if (
                hook.hook_type == HookType.FILTER
                and result.success
                and result.result is not None
            ):
                if len(args) > 0:
                    args = (result.result,) + args[1:]

        return results

    async def execute_filter(self, hook_name: str, value: Any, *args, **kwargs) -> Any:
        """Execute filter hooks.

        Args:
            hook_name: Hook name
            value: Value to filter
            *args: Additional arguments
            **kwargs: Additional keyword arguments

        Returns:
            Filtered value
        """
        hooks = self.registry.get_hooks(hook_name)

        if not hooks:
            return value

        filtered_value = value

        for hook in hooks:
            if not hook.enabled or hook.hook_type != HookType.FILTER:
                continue

            # Check conditions
            if hook.conditions and not self._check_conditions(
                hook.conditions, filtered_value, *args, **kwargs
            ):
                continue

            # Execute hook
            result = await self._execute_single(hook, filtered_value, *args, **kwargs)

            if result.success and result.result is not None:
                filtered_value = result.result

            # Record execution
            self._record_execution(hook, result, (filtered_value,) + args, kwargs)

        return filtered_value

    async def execute_pre_post(
        self, hook_name: str, func: Callable, *args, **kwargs
    ) -> Any:
        """Execute pre/post hooks around a function.

        Args:
            hook_name: Base hook name
            func: Function to wrap
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result
        """
        # Execute pre hooks
        pre_hook_name = f"{hook_name}.pre"
        pre_results = await self.execute(pre_hook_name, *args, **kwargs)

        # Check if any pre hook failed
        if any(not r.success for r in pre_results):
            raise Exception(f"Pre-hook failed for {hook_name}")

        # Execute main function
        if asyncio.iscoroutinefunction(func):
            result = await func(*args, **kwargs)
        else:
            result = func(*args, **kwargs)

        # Execute post hooks
        post_hook_name = f"{hook_name}.post"
        await self.execute(post_hook_name, result, *args, **kwargs)

        return result

    async def _execute_single(self, hook: Hook, *args, **kwargs) -> HookResult:
        """Execute a single hook.

        Args:
            hook: Hook to execute
            *args: Hook arguments
            **kwargs: Hook keyword arguments

        Returns:
            Execution result
        """
        start_time = time.time()

        try:
            if hook.async_hook:
                result = await hook.callback(*args, **kwargs)
            else:
                # Run sync hook in executor
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None, hook.callback, *args, **kwargs
                )

            execution_time = time.time() - start_time

            return HookResult(
                hook_name=hook.name,
                plugin_id=hook.plugin_id,
                success=True,
                result=result,
                execution_time=execution_time,
            )

        except Exception as e:
            execution_time = time.time() - start_time

            return HookResult(
                hook_name=hook.name,
                plugin_id=hook.plugin_id,
                success=False,
                error=str(e),
                execution_time=execution_time,
            )

    def _check_conditions(self, conditions: Dict, *args, **kwargs) -> bool:
        """Check if conditions are met.

        Args:
            conditions: Conditions to check
            *args: Hook arguments
            **kwargs: Hook keyword arguments

        Returns:
            True if conditions are met
        """
        # TODO: Implement condition checking logic
        # This could include checking argument values, system state, etc.
        return True

    def _record_execution(
        self, hook: Hook, result: HookResult, args: tuple, kwargs: dict
    ):
        """Record hook execution in database.

        Args:
            hook: Executed hook
            result: Execution result
            args: Hook arguments
            kwargs: Hook keyword arguments
        """
        conn = sqlite3.connect(self.registry.db_path)
        cursor = conn.cursor()

        # Serialize input/output data
        try:
            input_data = json.dumps({"args": args, "kwargs": kwargs}, default=str)
        except:
            input_data = None

        try:
            output_data = json.dumps(result.result, default=str)
        except:
            output_data = None

        cursor.execute(
            """
            INSERT INTO hook_executions
            (hook_name, plugin_id, triggered_at, execution_time, success,
             error_message, input_data, output_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                hook.name,
                hook.plugin_id,
                datetime.now(),
                result.execution_time,
                result.success,
                result.error,
                input_data,
                output_data,
            ),
        )

        conn.commit()
        conn.close()


class EventEmitter:
    """Event emitter for event-driven architecture."""

    def __init__(self, executor: HookExecutor):
        """Initialize event emitter.

        Args:
            executor: Hook executor
        """
        self.executor = executor
        self.event_queue = asyncio.Queue()
        self.event_handlers = defaultdict(list)
        self.running = False
        self.worker_task = None

    async def start(self):
        """Start event processing."""
        if self.running:
            return

        self.running = True
        self.worker_task = asyncio.create_task(self._process_events())

    async def stop(self):
        """Stop event processing."""
        self.running = False
        if self.worker_task:
            await self.worker_task

    async def emit(self, event: Event):
        """Emit an event.

        Args:
            event: Event to emit
        """
        await self.event_queue.put(event)

    def on(
        self,
        event_name: str,
        handler: Callable,
        priority: EventPriority = EventPriority.NORMAL,
    ):
        """Register event handler.

        Args:
            event_name: Event name or pattern
            handler: Event handler
            priority: Handler priority
        """
        self.event_handlers[event_name].append((priority, handler))
        self.event_handlers[event_name].sort(key=lambda x: x[0].value)

    def off(self, event_name: str, handler: Optional[Callable] = None):
        """Unregister event handler.

        Args:
            event_name: Event name
            handler: Specific handler to remove (None removes all)
        """
        if event_name not in self.event_handlers:
            return

        if handler is None:
            del self.event_handlers[event_name]
        else:
            self.event_handlers[event_name] = [
                (p, h) for p, h in self.event_handlers[event_name] if h != handler
            ]

    async def _process_events(self):
        """Process events from queue."""
        while self.running:
            try:
                # Get event with timeout
                event = await asyncio.wait_for(self.event_queue.get(), timeout=1.0)

                # Find matching handlers
                handlers = []

                # Exact match
                if event.name in self.event_handlers:
                    handlers.extend(self.event_handlers[event.name])

                # Pattern match (e.g., "device.*" matches "device.online")
                for pattern, pattern_handlers in self.event_handlers.items():
                    if "*" in pattern:
                        pattern_regex = pattern.replace(".", r"\.").replace("*", ".*")
                        import re

                        if re.match(pattern_regex, event.name):
                            handlers.extend(pattern_handlers)

                # Sort by priority
                handlers.sort(key=lambda x: x[0].value)

                # Execute handlers
                for priority, handler in handlers:
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            await handler(event)
                        else:
                            await asyncio.get_event_loop().run_in_executor(
                                None, handler, event
                            )
                    except Exception as e:
                        # Log error but continue processing
                        print(f"Error in event handler for {event.name}: {e}")

                # Execute event hooks
                await self.executor.execute(f"event.{event.name}", event)

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"Error processing event: {e}")


class HookManager:
    """Main hook manager combining registry, executor, and events."""

    def __init__(self, db_path: str = "kasa_monitor.db"):
        """Initialize hook manager.

        Args:
            db_path: Path to database
        """
        self.registry = HookRegistry(db_path)
        self.executor = HookExecutor(self.registry)
        self.emitter = EventEmitter(self.executor)
        self.decorators = {}

    async def start(self):
        """Start hook manager."""
        await self.emitter.start()

    async def stop(self):
        """Stop hook manager."""
        await self.emitter.stop()

    def hook(
        self,
        hook_name: str,
        hook_type: HookType = HookType.ACTION,
        priority: HookPriority = HookPriority.NORMAL,
        plugin_id: Optional[str] = None,
    ):
        """Decorator for registering hooks.

        Args:
            hook_name: Hook name
            hook_type: Hook type
            priority: Hook priority
            plugin_id: Plugin ID

        Returns:
            Decorator function
        """

        def decorator(func):
            hook = Hook(
                name=hook_name,
                callback=func,
                plugin_id=plugin_id,
                hook_type=hook_type,
                priority=priority,
                async_hook=asyncio.iscoroutinefunction(func),
            )
            self.registry.register(hook)

            # Store decorator reference
            self.decorators[func] = hook

            return func

        return decorator

    def pre_hook(self, hook_name: str, **kwargs):
        """Decorator for pre-hooks."""
        return self.hook(f"{hook_name}.pre", HookType.PRE, **kwargs)

    def post_hook(self, hook_name: str, **kwargs):
        """Decorator for post-hooks."""
        return self.hook(f"{hook_name}.post", HookType.POST, **kwargs)

    def filter_hook(self, hook_name: str, **kwargs):
        """Decorator for filter hooks."""
        return self.hook(hook_name, HookType.FILTER, **kwargs)

    async def call(self, hook_name: str, *args, **kwargs) -> List[HookResult]:
        """Call hooks by name.

        Args:
            hook_name: Hook name
            *args: Hook arguments
            **kwargs: Hook keyword arguments

        Returns:
            Hook results
        """
        return await self.executor.execute(hook_name, *args, **kwargs)

    async def filter(self, hook_name: str, value: Any, *args, **kwargs) -> Any:
        """Apply filter hooks.

        Args:
            hook_name: Hook name
            value: Value to filter
            *args: Additional arguments
            **kwargs: Additional keyword arguments

        Returns:
            Filtered value
        """
        return await self.executor.execute_filter(hook_name, value, *args, **kwargs)

    async def emit(
        self,
        event_name: str,
        data: Any,
        source: Optional[str] = None,
        priority: EventPriority = EventPriority.NORMAL,
        **metadata,
    ):
        """Emit an event.

        Args:
            event_name: Event name
            data: Event data
            source: Event source
            priority: Event priority
            **metadata: Additional metadata
        """
        event = Event(
            name=event_name,
            data=data,
            source=source,
            priority=priority,
            metadata=metadata if metadata else None,
        )
        await self.emitter.emit(event)

    def on(
        self,
        event_name: str,
        handler: Callable,
        priority: EventPriority = EventPriority.NORMAL,
    ):
        """Register event handler.

        Args:
            event_name: Event name or pattern
            handler: Event handler
            priority: Handler priority
        """
        self.emitter.on(event_name, handler, priority)

    def off(self, event_name: str, handler: Optional[Callable] = None):
        """Unregister event handler.

        Args:
            event_name: Event name
            handler: Specific handler to remove
        """
        self.emitter.off(event_name, handler)

    def get_statistics(
        self, hook_name: Optional[str] = None, days: int = 7
    ) -> Dict[str, Any]:
        """Get hook execution statistics.

        Args:
            hook_name: Filter by hook name
            days: Number of days to analyze

        Returns:
            Execution statistics
        """
        conn = sqlite3.connect(self.registry.db_path)
        cursor = conn.cursor()

        query = """
            SELECT 
                hook_name,
                COUNT(*) as total_executions,
                AVG(execution_time) as avg_time,
                MAX(execution_time) as max_time,
                MIN(execution_time) as min_time,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed
            FROM hook_executions
            WHERE triggered_at > datetime('now', '-{} days')
        """.format(
            days
        )

        if hook_name:
            query += " AND hook_name = ?"
            cursor.execute(query + " GROUP BY hook_name", (hook_name,))
        else:
            cursor.execute(query + " GROUP BY hook_name")

        stats = {}
        for row in cursor.fetchall():
            stats[row[0]] = {
                "total_executions": row[1],
                "avg_execution_time": row[2],
                "max_execution_time": row[3],
                "min_execution_time": row[4],
                "successful": row[5],
                "failed": row[6],
                "success_rate": (row[5] / row[1] * 100) if row[1] > 0 else 0,
            }

        conn.close()
        return stats

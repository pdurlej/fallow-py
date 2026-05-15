# protocol-class

Tests structural typing protocols.

Expected behavior: `Service` must not be reported as unused implementation code.

Why this is tough: protocol classes often describe shape for external type checkers and may not be
instantiated directly.

How fallow-py handles it: Protocol bases are skipped by the dead-code symbol heuristic by default.

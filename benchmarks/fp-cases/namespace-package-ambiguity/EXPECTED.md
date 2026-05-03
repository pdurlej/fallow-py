# namespace-package-ambiguity

Tests two configured roots that map different files to the same namespace package module.

Expected behavior: pyfallow reports the module ambiguity. Any related dead-code signal must stay low
confidence.

Why this is tough: PEP 420 namespace packages can merge roots at runtime, while static analysis must pick
a deterministic file for a module id.

How pyfallow handles it: module ambiguity evidence is emitted in analysis metadata.

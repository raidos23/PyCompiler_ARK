import fnmatch
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class PreCompileContext:
    """Contexte passé aux plugins.

    Donne accès aux données du workspace et fournit des outils de recherche de fichiers.
    """

    root: Path
    config: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    build_context: Optional[Any] = None
    _iter_cache: dict[tuple[tuple[str, ...], tuple[str, ...]], list[Path]] = field(
        default_factory=dict, repr=False, compare=False
    )

    @property
    def project_root(self) -> Path:
        """Alias pour root (compatibilité)."""
        return self.root

    @property
    def name(self) -> str:
        return self.root.name

    @property
    def file_patterns(self) -> tuple[str, ...]:
        """Patterns d'inclusion (depuis bcasl.yml)."""
        patterns = self.config.get("file_patterns", ["**/*.py"])
        return tuple(patterns) if patterns else ("**/*.py",)

    @property
    def exclude_patterns(self) -> tuple[str, ...]:
        """Patterns d'exclusion (depuis bcasl.yml)."""
        patterns = self.config.get("exclude_patterns", [])
        return tuple(patterns) if patterns else ()

    def iter_files(
        self,
        include: Optional[Iterable[str]] = None,
        exclude: Optional[Iterable[str]] = None,
    ) -> Iterable[Path]:
        """Itère sur les fichiers du projet.

        Par défaut, utilise les patterns de configuration (bcasl.yml).
        """
        inc = tuple(include) if include is not None else self.file_patterns
        exc = tuple(exclude) if exclude is not None else self.exclude_patterns

        opt = self.config.get("options", {}) if isinstance(self.config, dict) else {}
        enable_cache = bool(opt.get("iter_files_cache", True))

        cache_key = None
        if enable_cache:
            try:
                cache_key = (tuple(sorted(inc)), tuple(sorted(exc)))
                if cache_key in self._iter_cache:
                    yield from self._iter_cache[cache_key]
                    return
            except Exception:
                enable_cache = False

        def is_excluded(p: Path) -> bool:
            try:
                rel = p.relative_to(self.root).as_posix()
            except ValueError:
                rel = p.as_posix()
            return any(fnmatch.fnmatch(rel, pat) for pat in exc)

        seen: set[Path] = set()
        collected: list[Path] = []

        for pat in inc:
            try:
                for path in self.root.glob(pat):
                    if path.is_file() and not is_excluded(path):
                        resolved = path.resolve()
                        if resolved not in seen:
                            seen.add(resolved)
                            collected.append(path)
                            yield path
            except (OSError, ValueError):
                continue

        if enable_cache and cache_key is not None:
            self._iter_cache[cache_key] = collected

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1
from pathlib import Path
import json
import subprocess

from dos_machines.application.engine_support import (
    bundled_default_config_path,
    detect_engine_version,
    display_name_for_engine,
    engine_id_prefix,
)
from dos_machines.application.schema_parser import ConfigSchemaParser
from dos_machines.domain.models import AppPaths, EngineCapabilities, EngineRef, EngineSchema


@dataclass(slots=True)
class EngineCache:
    ref: EngineRef
    root: Path
    binary_info_path: Path
    default_conf_path: Path
    schema_path: Path


class EngineRegistry:
    def __init__(self, app_paths: AppPaths) -> None:
        self._app_paths = app_paths
        self._parser = ConfigSchemaParser()

    def register(self, binary_path: Path) -> EngineCache:
        resolved = binary_path.expanduser().resolve()
        if not resolved.exists():
            raise FileNotFoundError(f"Engine binary does not exist: {resolved}")

        version = detect_engine_version(resolved)
        engine_id = self._engine_id_for_path(resolved, version)
        engine_root = self._app_paths.engines_root / engine_id
        engine_root.mkdir(parents=True, exist_ok=True)

        ref = EngineRef(
            engine_id=engine_id,
            binary_path=resolved,
            display_name=display_name_for_engine(version),
            version=version,
            probe_status="cached",
            capabilities=self._detect_capabilities(resolved),
        )
        cache = EngineCache(
            ref=ref,
            root=engine_root,
            binary_info_path=engine_root / "binary-info.json",
            default_conf_path=engine_root / "default.conf",
            schema_path=engine_root / "schema.json",
        )
        default_config_text = self._load_default_config_text(resolved)
        cache.default_conf_path.write_text(default_config_text, encoding="utf-8")
        schema = self._parser.parse_text(default_config_text, engine_id=engine_id, display_name=ref.display_name)

        cache.binary_info_path.write_text(
            json.dumps(
                {
                    **ref.to_json(),
                    "resolved_path": str(resolved),
                    "exists_on_registration": True,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        cache.schema_path.write_text(
            json.dumps(schema.to_json(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return cache

    def load_schema(self, engine_id: str) -> EngineSchema:
        schema_path = self._app_paths.engines_root / engine_id / "schema.json"
        payload = json.loads(schema_path.read_text(encoding="utf-8"))
        return EngineSchema.from_json(payload)

    def _engine_id_for_path(self, binary_path: Path, version: str | None = None) -> str:
        digest = sha1(str(binary_path).encode("utf-8")).hexdigest()[:12]
        return f"{engine_id_prefix(version)}-{digest}"

    def _detect_capabilities(self, binary_path: Path) -> EngineCapabilities:
        glshaders = self._list_glshaders(binary_path)
        return EngineCapabilities(
            munt_available=False,
            fluidsynth_available=False,
            glshader_support=bool(glshaders),
            glshaders=glshaders,
        )

    def _list_glshaders(self, binary_path: Path) -> list[str]:
        try:
            completed = subprocess.run(
                [str(binary_path), "--list-glshaders"],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
        except (OSError, subprocess.SubprocessError):
            return []
        lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
        return [line for line in lines if not line.startswith("--")]

    def _load_default_config_text(self, binary_path: Path) -> str:
        bundled = bundled_default_config_path()
        if bundled is not None:
            return bundled.read_text(encoding="utf-8")
        return f"# No bundled config sample found for {display_name_for_engine()}.\n"

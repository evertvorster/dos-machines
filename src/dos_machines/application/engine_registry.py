from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha1
from pathlib import Path
import json
import shutil
import subprocess

from dos_machines.domain.models import AppPaths, EngineRef


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

    def register(self, binary_path: Path) -> EngineCache:
        resolved = binary_path.expanduser().resolve()
        if not resolved.exists():
            raise FileNotFoundError(f"Engine binary does not exist: {resolved}")

        engine_id = self._engine_id_for_path(resolved)
        engine_root = self._app_paths.engines_root / engine_id
        engine_root.mkdir(parents=True, exist_ok=True)

        ref = EngineRef(
            engine_id=engine_id,
            binary_path=resolved,
            display_name="DOSBox Staging",
            version=self._detect_version(resolved),
            probe_status="cached",
        )
        cache = EngineCache(
            ref=ref,
            root=engine_root,
            binary_info_path=engine_root / "binary-info.json",
            default_conf_path=engine_root / "default.conf",
            schema_path=engine_root / "schema.json",
        )

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
        if not cache.default_conf_path.exists():
            cache.default_conf_path.write_text(
                "# Placeholder default DOSBox Staging config cache.\n",
                encoding="utf-8",
            )
        if not cache.schema_path.exists():
            cache.schema_path.write_text(
                json.dumps(
                    {
                        "engine_id": engine_id,
                        "display_name": ref.display_name,
                        "sections": [],
                        "probe_status": "placeholder",
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
        return cache

    def _engine_id_for_path(self, binary_path: Path) -> str:
        digest = sha1(str(binary_path).encode("utf-8")).hexdigest()[:12]
        return f"staging-{digest}"

    def _detect_version(self, binary_path: Path) -> str | None:
        if shutil.which(binary_path.name) is None and not binary_path.exists():
            return None
        try:
            completed = subprocess.run(
                [str(binary_path), "--version"],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
        except (OSError, subprocess.SubprocessError):
            return None

        output = (completed.stdout or completed.stderr).strip().splitlines()
        return output[0].strip() if output else None

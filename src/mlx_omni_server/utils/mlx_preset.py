import json
from pathlib import Path

class PresetManager:
    """Utility class to manage sampling preset configurations.

    The configuration is stored in ``src/mlx_omni_server/mlx_preset/config.json``.
    It provides convenient accessors for model-specific presets, slug-based
    presets and a simple update mechanism.
    """

    _config_path = Path(__file__).parent.parent / "mlx_preset" / "config.json"
    _cache = None

    @classmethod
    def _load_config(cls):
        """Load the JSON configuration lazily.

        Returns:
            dict: Parsed config content.
        """
        if cls._cache is None:
            with cls._config_path.open("r", encoding="utf-8") as f:
                cls._cache = json.load(f)
        return cls._cache

    @classmethod
    def get_preset_by_model_name(cls, model_name: str) -> dict:
        """Return the preset for a specific model.

        Args:
            model_name: Key under ``"preset"`` in the JSON.

        Returns:
            dict of sampling parameters or empty dict if not found.
        """
        cfg = cls._load_config()
        return cfg.get("preset", {}).get(model_name, {})

    @classmethod
    def get_preset_by_slug_and_mode(cls, slug: str, mode: str) -> dict:
        """Retrieve a preset defined for a UI slug and mode.

        Args:
            slug: Top-level key under ``"slug_preset"``.
            mode: Sub-key inside the slug (e.g., "code", "architect").

        Returns:
            dict of parameters or empty dict.
        """
        cfg = cls._load_config()
        return cfg.get("slug_preset", {}).get(slug, {}).get(mode, {})

    @classmethod
    def get_default_preset(cls) -> dict:
        """Return the generic default model preset.
        """
        cfg = cls._load_config()
        return cfg.get("preset", {}).get("model_default", {})

    @classmethod
    def update_preset(cls, key_path: list[str], value) -> None:
        """Update a nested preset entry and persist the change.

        ``key_path`` is a list of keys leading to the target field, e.g.
        ``["preset", "model_default", "temp"]``.
        """
        cfg = cls._load_config()
        d = cfg
        for key in key_path[:-1]:
            d = d.setdefault(key, {})
        d[key_path[-1]] = value
        # Write back to file
        with cls._config_path.open("w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
        cls._cache = cfg

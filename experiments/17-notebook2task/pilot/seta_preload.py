# Extracted unchanged functions from SETA 5868a1b claude_agents.py; Apache-2.0.
import os
import glob

def _read_file_safe(path: str) -> str | None:
    """Return file contents or None if missing/unreadable."""
    try:
        with open(path, "r") as f:
            return f.read()
    except Exception:
        return None

def _seed_adapter_kaggle(seed_data_folder: str) -> str:
    """Adapter for Kaggle notebook seeds with local dataset support.

    Inlines:
      - kernel-metadata.json (small, ~5KB)
      - datasets/*/manifest.json (dataset metadata, ~1KB each)
      - List of actual data files (CSV, parquet, etc.) in each dataset folder

    Describes (for Read tool):
      - Notebook .ipynb file (can be large, 1-5MB)

    All datasets are pre-downloaded locally — agent loads from datasets/ folder.
    """
    parts: list[str] = []

    # 1. Preload kernel metadata
    meta_content = _read_file_safe(os.path.join(seed_data_folder, "kernel-metadata.json"))
    if meta_content:
        parts.append(f"### kernel-metadata.json (preloaded)\n```json\n{meta_content}\n```")

    # 2. Preload dataset manifests and list available data files
    datasets_dir = os.path.join(seed_data_folder, "datasets")
    if os.path.exists(datasets_dir):
        datasets_info = []
        for dataset_dir in sorted(os.listdir(datasets_dir)):
            dataset_path = os.path.join(datasets_dir, dataset_dir)
            if not os.path.isdir(dataset_path):
                continue

            # Preload manifest
            manifest_file = os.path.join(dataset_path, "manifest.json")
            manifest_content = None
            if os.path.exists(manifest_file):
                manifest_content = _read_file_safe(manifest_file)

            # List actual data files (CSV, parquet, JSON, etc.)
            data_files = []
            for fname in sorted(os.listdir(dataset_path)):
                fpath = os.path.join(dataset_path, fname)
                if os.path.isfile(fpath) and fname != "manifest.json":
                    size_kb = os.path.getsize(fpath) // 1024
                    data_files.append(f"  - `{fname}` ({size_kb} KB)")

            if manifest_content or data_files:
                datasets_info.append({
                    'name': dataset_dir,
                    'manifest': manifest_content,
                    'files': data_files
                })

        if datasets_info:
            parts.append("### Datasets (Preloaded & Available Locally)")
            for ds_info in datasets_info:
                parts.append(f"#### {ds_info['name']}/")
                if ds_info['manifest']:
                    parts.append(f"**Manifest:**\n```json\n{ds_info['manifest']}\n```")
                if ds_info['files']:
                    parts.append("**Available data files:**")
                    parts.append("\n".join(ds_info['files']))

    # 3. Extract notebook structure (cell summaries) to avoid repeated reads
    notebook_structure = []
    for ext in ("*.ipynb",):
        for notebook_path in sorted(glob.glob(os.path.join(seed_data_folder, ext))):
            try:
                import json
                with open(notebook_path, 'r', encoding='utf-8') as f:
                    notebook = json.load(f)

                # Extract cell structure
                cells_summary = []
                for i, cell in enumerate(notebook.get('cells', [])[:20]):  # First 20 cells
                    cell_type = cell.get('cell_type', 'unknown')
                    if cell_type == 'markdown':
                        source_text = ''.join(cell.get('source', [])).strip()
                        # Extract heading if present
                        if source_text.startswith('#'):
                            heading = source_text.split('\n')[0][:60]
                            cells_summary.append(f"  {i+1}. [Markdown] {heading}")
                    elif cell_type == 'code':
                        source_text = ''.join(cell.get('source', []))
                        # Extract first meaningful line or function call
                        first_line = [l.strip() for l in source_text.split('\n') if l.strip() and not l.strip().startswith('#')][0] if source_text.strip() else ''
                        if first_line:
                            preview = first_line[:70]
                            cells_summary.append(f"  {i+1}. [Code] {preview}...")

                if cells_summary:
                    notebook_structure.append(
                        f"### Notebook Structure ({os.path.basename(notebook_path)})\n"
                        + "First 20 cells (read file directly if you need full details):\n"
                        + "\n".join(cells_summary)
                    )
            except Exception as e:
                pass  # Fallback if notebook parsing fails

    # 4. Describe notebook files (agent reads with Read tool if needed)
    notebook_files = []
    for ext in ("*.ipynb",):
        for p in sorted(glob.glob(os.path.join(seed_data_folder, ext))):
            size_kb = os.path.getsize(p) // 1024
            notebook_files.append(
                f"- `{os.path.basename(p)}` ({size_kb} KB) — read with the Read tool if needed"
            )

    # Add notebook structure summary before asking agent to read
    if notebook_structure:
        parts.extend(notebook_structure)

    if notebook_files:
        parts.append(
            "### Notebook File\n"
            + "Full notebook: " + "\n".join(notebook_files) + "\n\n"
            + "Use the Read tool ONLY if you need specific cell details beyond the structure above."
        )

    if not parts:
        return ""

    return (
        "## Seed Data\n\n"
        + "\n\n".join(parts)
        + "\n\n> **Datasets are pre-downloaded and ready to load from local folders.** "
        "kernel-metadata.json and manifests are preloaded above. "
        "Use the Read tool to examine the notebook file if needed."
    )

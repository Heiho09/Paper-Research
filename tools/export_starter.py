"""Export only reusable code/config/docs, never operational history or secrets."""
import argparse
import hashlib
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]


def export(output):
    paths = [ROOT / p for p in (
        '.gitignore', 'AGENTS.md', 'config/settings.json',
        'examples/style-guide.md', 'tools/export_starter.py',
    )]
    for directory, pattern in (
        ('paper_research', '*.py'), ('tests', '*.py'),
        ('.github/workflows', '*.yml'), ('docs', '*.md'),
    ):
        paths.extend(sorted((ROOT / directory).glob(pattern)))
    for name in ('LICENSE', 'LICENSE.md', 'LICENSE.txt'):
        if (ROOT / name).is_file():
            paths.append(ROOT / name)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, 'w', compression=ZIP_DEFLATED) as archive:
        archive.writestr('weekly-research-starter/README.md', (ROOT / 'docs/STARTER_README.ko.md').read_bytes())
        for path in paths:
            if path.is_symlink() or not path.is_file():
                raise ValueError(f'Expected a regular file: {path.relative_to(ROOT)}')
            archive.write(path, 'weekly-research-starter/' + path.relative_to(ROOT).as_posix())
        if not any(p.name.startswith('LICENSE') for p in paths):
            archive.writestr('weekly-research-starter/DISTRIBUTION-NOTE.md',
                '# Distribution status\n\nNo license has been selected in this preparation package. '
                'The owner should choose terms before public distribution. '
                'Third-party research content retains its own terms.\n')
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    print(f'{output}\nSHA256 {digest}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'build/weekly-research-starter.zip')
    export(parser.parse_args().output)

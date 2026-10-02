"""Собирает сайт для публикации в папку dist/.

В dist попадает:
  - сайт-витрина (папка showcase) — в корень;
  - демо лендинга (projects/02-landing-template) — в dist/demos/landing/, чтобы кнопка «Демо» на витрине работала;
  - пример адаптации под стоматологию — в dist/demos/landing-dental/;
  - дизайн-концепция SaaS-лендинга (projects/05-saas-landing-concept) — в dist/demos/saas-concept/.

Запуск из корня портфолио:
    python scripts/build_site.py
Посмотреть результат так, как его увидят посетители:
    python -m http.server 8000 --directory dist
"""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"

# Что копировать в демо лендинга (README и прочее для посетителей не нужно)
LANDING_FILES = ["index.html", "style.css", "script.js", "site.config.js", "assets"]


def copy(src: Path, dst: Path) -> None:
    if src.is_dir():
        shutil.copytree(src, dst)
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def main() -> None:
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()

    for item in (ROOT / "showcase").iterdir():
        copy(item, DIST / item.name)

    landing = ROOT / "projects" / "02-landing-template"
    for name in LANDING_FILES:
        copy(landing / name, DIST / "demos" / "landing" / name)

    # Примеры и дизайн-концепция: каждый в своей папке внутри demos/
    for name in LANDING_FILES:
        copy(landing / "examples" / "dental" / name, DIST / "demos" / "landing-dental" / name)
    concept = ROOT / "projects" / "05-saas-landing-concept"
    for name in ["index.html", "style.css"]:
        copy(concept / name, DIST / "demos" / "saas-concept" / name)

    # Отключает обработку Jekyll на GitHub Pages: файлы отдаются как есть
    (DIST / ".nojekyll").write_text("", encoding="utf-8")

    files = [p for p in DIST.rglob("*") if p.is_file()]
    size_kb = sum(p.stat().st_size for p in files) / 1024
    print(f"Готово: {DIST} ({len(files)} файлов, {size_kb:.0f} КБ)")


if __name__ == "__main__":
    main()

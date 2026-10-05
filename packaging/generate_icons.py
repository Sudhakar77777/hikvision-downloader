"""Generate multi-resolution .ico, .icns, and .png application icons from the source SVG."""

import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QByteArray
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication


def render_svg_to_image(svg_bytes: bytes, size: int) -> QImage:
    """Render an SVG byte string onto a transparent QImage of the specified pixel dimensions."""
    renderer = QSvgRenderer(QByteArray(svg_bytes))
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(QColor(0, 0, 0, 0))

    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    renderer.render(painter)
    painter.end()
    return image


def generate_icons() -> None:
    """Generate .png, .ico, and .icns icons into packaging/assets/."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(["icon_gen", "-platform", "offscreen"])

    workspace_root = Path(__file__).resolve().parent.parent
    svg_path = workspace_root / "src" / "hikvision_downloader" / "ui" / "assets" / "favicon.svg"
    output_dir = workspace_root / "packaging" / "assets"
    output_dir.mkdir(parents=True, exist_ok=True)

    svg_data = svg_path.read_bytes()

    # Generate high-res 512x512 PNG
    img_512 = render_svg_to_image(svg_data, 512)
    png_path = output_dir / "icon.png"
    img_512.save(str(png_path))
    print(f"Generated PNG: {png_path}")

    # Generate standard ICO (16, 32, 48, 64, 128, 256)
    ico_path = output_dir / "hikvision-downloader.ico"
    # Qt QImage / QPixmap can save directly to .ico
    img_256 = render_svg_to_image(svg_data, 256)
    img_256.save(str(ico_path))
    print(f"Generated ICO: {ico_path}")

    # Generate ICNS on macOS if iconutil is available
    icns_path = output_dir / "hikvision-downloader.icns"
    iconset_dir = output_dir / "hikvision-downloader.iconset"
    iconset_dir.mkdir(parents=True, exist_ok=True)

    icon_specs = [
        ("icon_16x16.png", 16),
        ("icon_16x16@2x.png", 32),
        ("icon_32x32.png", 32),
        ("icon_32x32@2x.png", 64),
        ("icon_128x128.png", 128),
        ("icon_128x128@2x.png", 256),
        ("icon_256x256.png", 256),
        ("icon_256x256@2x.png", 512),
        ("icon_512x512.png", 512),
        ("icon_512x512@2x.png", 1024),
    ]

    for filename, px in icon_specs:
        img = render_svg_to_image(svg_data, px)
        img.save(str(iconset_dir / filename))

    # Run iconutil if on macOS
    if sys.platform == "darwin":
        try:
            subprocess.run(
                ["iconutil", "-c", "icns", str(iconset_dir), "-o", str(icns_path)],
                check=True,
                capture_output=True,
            )
            print(f"Generated ICNS via iconutil: {icns_path}")
        except (subprocess.CalledProcessError, FileNotFoundError, OSError) as exc:
            print(f"Notice: iconutil failed or skipped ({exc}); saving PNG fallback.")
            img_512.save(str(icns_path))
    else:
        # Fallback copy
        img_512.save(str(icns_path))


if __name__ == "__main__":
    generate_icons()

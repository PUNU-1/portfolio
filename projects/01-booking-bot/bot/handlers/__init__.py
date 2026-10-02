"""Роутеры бота. Порядок важен: сначала специфичные, запасной — последним."""
from . import admin, booking, fallback

routers = [admin.router, booking.router, fallback.router]

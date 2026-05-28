#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PlantaOS install_v14 — Mobile menu real (hamburger + drawer fullscreen)

Substitui apenas frontend/components/v2/TopBar.tsx:
  - Desktop (≥920px): nav linear horizontal como antes
  - Mobile (<920px): logo + botão hamburger 42x42
  - Click no hamburger abre drawer fullscreen com:
    * pill SIMULADO + relógio no topo
    * 9 links em listagem grande (22px Inter)
    * Indicador verde no link activo
    * Footer "× Rock in Rio Lisboa 2026"
  - Body scroll bloqueado quando drawer aberto
  - Drawer fecha automaticamente ao navegar
  - ESC implícito via click num link
  - Phone pequeno (≤380px): brand truncada com ellipsis
"""

import base64, os, shutil, subprocess, sys
from datetime import datetime
from pathlib import Path

os.environ["PATH"] = ":".join([
    "/usr/bin", "/bin", "/usr/sbin", "/sbin",
    "/usr/local/bin", "/opt/homebrew/bin",
    os.environ.get("PATH", ""),])

TOPBAR_B64 = (
    'J3VzZSBjbGllbnQnOwoKaW1wb3J0IExpbmsgZnJvbSAnbmV4dC9saW5rJzsKaW1wb3J0IHsgdXNl'
    'UGF0aG5hbWUgfSBmcm9tICduZXh0L25hdmlnYXRpb24nOwppbXBvcnQgeyB1c2VFZmZlY3QsIHVz'
    'ZVN0YXRlIH0gZnJvbSAncmVhY3QnOwoKY29uc3QgTkFWID0gWwogIHsgaHJlZjogJy92MicsICAg'
    'ICAgICAgICBsYWJlbDogJ0luw61jaW8nIH0sCiAgeyBocmVmOiAnL3YyL3R3aW4nLCAgICAgIGxh'
    'YmVsOiAnVHdpbicgfSwKICB7IGhyZWY6ICcvdjIvc2Vuc29ycycsICAgbGFiZWw6ICdTZW5zb3Jl'
    'cycgfSwKICB7IGhyZWY6ICcvdjIvc2hvd3MnLCAgICAgbGFiZWw6ICdTaG93cycgfSwKICB7IGhy'
    'ZWY6ICcvdjIvb3BlcmF0aW9ucycsbGFiZWw6ICdPcGVyYcOnw7VlcycgfSwKICB7IGhyZWY6ICcv'
    'djIvY2xlYW5pbmcnLCAgbGFiZWw6ICdMaW1wZXphJyB9LAogIHsgaHJlZjogJy92Mi9pbmNpZGVu'
    'dHMnLCBsYWJlbDogJ0luY2lkZW50ZXMnIH0sCiAgeyBocmVmOiAnL3YyL3Njb3InLCAgICAgIGxh'
    'YmVsOiAnU0NPUicgfSwKICB7IGhyZWY6ICcvdjIvcGlwZWxpbmVzJywgbGFiZWw6ICdQaXBlbGlu'
    'ZXMnIH0sCl07CgpleHBvcnQgZGVmYXVsdCBmdW5jdGlvbiBUb3BCYXIoKSB7CiAgY29uc3QgcGF0'
    'aG5hbWUgPSB1c2VQYXRobmFtZSgpIHx8ICcvdjInOwogIGNvbnN0IFt0aW1lLCBzZXRUaW1lXSA9'
    'IHVzZVN0YXRlKCcnKTsKICBjb25zdCBbbW9iaWxlT3Blbiwgc2V0TW9iaWxlT3Blbl0gPSB1c2VT'
    'dGF0ZShmYWxzZSk7CgogIHVzZUVmZmVjdCgoKSA9PiB7CiAgICBjb25zdCB0aWNrID0gKCkgPT4g'
    'ewogICAgICBjb25zdCBkID0gbmV3IERhdGUoKTsKICAgICAgc2V0VGltZSgKICAgICAgICBgJHtT'
    'dHJpbmcoZC5nZXRIb3VycygpKS5wYWRTdGFydCgyLCAnMCcpfToke1N0cmluZyhkLmdldE1pbnV0'
    'ZXMoKSkucGFkU3RhcnQoMiwgJzAnKX06JHtTdHJpbmcoZC5nZXRTZWNvbmRzKCkpLnBhZFN0YXJ0'
    'KDIsICcwJyl9YCwKICAgICAgKTsKICAgIH07CiAgICB0aWNrKCk7CiAgICBjb25zdCBpdiA9IHNl'
    'dEludGVydmFsKHRpY2ssIDEwMDApOwogICAgcmV0dXJuICgpID0+IGNsZWFySW50ZXJ2YWwoaXYp'
    'OwogIH0sIFtdKTsKCiAgLy8gRmVjaGFyIGRyYXdlciBhbyBuYXZlZ2FyCiAgdXNlRWZmZWN0KCgp'
    'ID0+IHsgc2V0TW9iaWxlT3BlbihmYWxzZSk7IH0sIFtwYXRobmFtZV0pOwoKICAvLyBCbG9xdWVh'
    'ciBzY3JvbGwgZG8gYm9keSBxdWFuZG8gZHJhd2VyIGFiZXJ0bwogIHVzZUVmZmVjdCgoKSA9PiB7'
    'CiAgICBpZiAobW9iaWxlT3BlbikgewogICAgICBkb2N1bWVudC5ib2R5LnN0eWxlLm92ZXJmbG93'
    'ID0gJ2hpZGRlbic7CiAgICB9IGVsc2UgewogICAgICBkb2N1bWVudC5ib2R5LnN0eWxlLm92ZXJm'
    'bG93ID0gJyc7CiAgICB9CiAgICByZXR1cm4gKCkgPT4geyBkb2N1bWVudC5ib2R5LnN0eWxlLm92'
    'ZXJmbG93ID0gJyc7IH07CiAgfSwgW21vYmlsZU9wZW5dKTsKCiAgY29uc3QgaXNBY3RpdmUgPSAo'
    'aHJlZjogc3RyaW5nKSA9PgogICAgaHJlZiA9PT0gJy92MicgPyBwYXRobmFtZSA9PT0gJy92Micg'
    'OiBwYXRobmFtZS5zdGFydHNXaXRoKGhyZWYpOwoKICByZXR1cm4gKAogICAgPD4KICAgICAgey8q'
    'IEhFQURFUiBGSVhPICovfQogICAgICA8aGVhZGVyCiAgICAgICAgc3R5bGU9e3sKICAgICAgICAg'
    'IHBvc2l0aW9uOiAnZml4ZWQnLAogICAgICAgICAgdG9wOiAwLAogICAgICAgICAgbGVmdDogMCwK'
    'ICAgICAgICAgIHJpZ2h0OiAwLAogICAgICAgICAgaGVpZ2h0OiAndmFyKC0taGVhZGVyLWgsIDcy'
    'cHgpJywKICAgICAgICAgIGJhY2tncm91bmQ6ICdyZ2JhKDI1NSwgMjU1LCAyNTUsIDAuOTQpJywK'
    'ICAgICAgICAgIGJhY2tkcm9wRmlsdGVyOiAnYmx1cigxNnB4KSBzYXR1cmF0ZSgxNDAlKScsCiAg'
    'ICAgICAgICBXZWJraXRCYWNrZHJvcEZpbHRlcjogJ2JsdXIoMTZweCkgc2F0dXJhdGUoMTQwJSkn'
    'LAogICAgICAgICAgYm9yZGVyQm90dG9tOiAnMXB4IHNvbGlkIHZhcigtLWJvcmRlciknLAogICAg'
    'ICAgICAgekluZGV4OiAxMDAsCiAgICAgICAgICBkaXNwbGF5OiAnZmxleCcsCiAgICAgICAgICBh'
    'bGlnbkl0ZW1zOiAnY2VudGVyJywKICAgICAgICAgIHBhZGRpbmc6ICcwIGNsYW1wKDE0cHgsIDN2'
    'dywgMzJweCknLAogICAgICAgICAgZ2FwOiAnY2xhbXAoMTBweCwgMnZ3LCAyNHB4KScsCiAgICAg'
    'ICAgfX0KICAgICAgPgogICAgICAgIHsvKiBMT0dPICsgQlJBTkQgKi99CiAgICAgICAgPExpbmsK'
    'ICAgICAgICAgIGhyZWY9Ii92MiIKICAgICAgICAgIHN0eWxlPXt7CiAgICAgICAgICAgIGRpc3Bs'
    'YXk6ICdmbGV4JywKICAgICAgICAgICAgYWxpZ25JdGVtczogJ2NlbnRlcicsCiAgICAgICAgICAg'
    'IGdhcDogMTAsCiAgICAgICAgICAgIHRleHREZWNvcmF0aW9uOiAnbm9uZScsCiAgICAgICAgICAg'
    'IGZsZXhTaHJpbms6IDAsCiAgICAgICAgICAgIG1pbldpZHRoOiAwLAogICAgICAgICAgfX0KICAg'
    'ICAgICA+CiAgICAgICAgICA8aW1nCiAgICAgICAgICAgIHNyYz0iL3BsYW50YS1sb2dvLnN2ZyIK'
    'ICAgICAgICAgICAgYWx0PSJQbGFudGEgU21hcnQgSG9tZXMiCiAgICAgICAgICAgIHN0eWxlPXt7'
    'CiAgICAgICAgICAgICAgd2lkdGg6ICdjbGFtcCgzNnB4LCA0dncsIDQ0cHgpJywKICAgICAgICAg'
    'ICAgICBoZWlnaHQ6ICdjbGFtcCgzNnB4LCA0dncsIDQ0cHgpJywKICAgICAgICAgICAgICBkaXNw'
    'bGF5OiAnYmxvY2snLAogICAgICAgICAgICAgIG9iamVjdEZpdDogJ2NvbnRhaW4nLAogICAgICAg'
    'ICAgICAgIGZsZXhTaHJpbms6IDAsCiAgICAgICAgICAgIH19CiAgICAgICAgICAvPgogICAgICAg'
    'ICAgPHNwYW4KICAgICAgICAgICAgY2xhc3NOYW1lPSJ0b3BiYXItYnJhbmQiCiAgICAgICAgICAg'
    'IHN0eWxlPXt7CiAgICAgICAgICAgICAgZm9udFNpemU6ICdjbGFtcCgxNHB4LCAxLjR2dywgMThw'
    'eCknLAogICAgICAgICAgICAgIGZvbnRXZWlnaHQ6IDYwMCwKICAgICAgICAgICAgICBjb2xvcjog'
    'J3ZhcigtLWluayknLAogICAgICAgICAgICAgIGxldHRlclNwYWNpbmc6ICctMC4wMmVtJywKICAg'
    'ICAgICAgICAgICB3aGl0ZVNwYWNlOiAnbm93cmFwJywKICAgICAgICAgICAgICBmb250RmFtaWx5'
    'OiAndmFyKC0tZm9udC1kaXNwbGF5LCBJbnRlciwgc2Fucy1zZXJpZiknLAogICAgICAgICAgICAg'
    'IG92ZXJmbG93OiAnaGlkZGVuJywKICAgICAgICAgICAgICB0ZXh0T3ZlcmZsb3c6ICdlbGxpcHNp'
    'cycsCiAgICAgICAgICAgIH19CiAgICAgICAgICA+CiAgICAgICAgICAgIFBsYW50YSBTbWFydCBI'
    'b21lcwogICAgICAgICAgPC9zcGFuPgogICAgICAgIDwvTGluaz4KCiAgICAgICAgey8qIE5BViBk'
    'ZXNrdG9wICovfQogICAgICAgIDxuYXYKICAgICAgICAgIGNsYXNzTmFtZT0idG9wYmFyLW5hdi1k'
    'ZXNrdG9wIgogICAgICAgICAgc3R5bGU9e3sKICAgICAgICAgICAgZGlzcGxheTogJ2ZsZXgnLAog'
    'ICAgICAgICAgICBnYXA6IDIsCiAgICAgICAgICAgIGZsZXg6IDEsCiAgICAgICAgICAgIG92ZXJm'
    'bG93WDogJ2F1dG8nLAogICAgICAgICAgICBzY3JvbGxiYXJXaWR0aDogJ25vbmUnLAogICAgICAg'
    'ICAgICBtc092ZXJmbG93U3R5bGU6ICdub25lJywKICAgICAgICAgICAganVzdGlmeUNvbnRlbnQ6'
    'ICdmbGV4LWVuZCcsCiAgICAgICAgICB9fQogICAgICAgID4KICAgICAgICAgIHtOQVYubWFwKChp'
    'dGVtKSA9PiB7CiAgICAgICAgICAgIGNvbnN0IGFjdGl2ZSA9IGlzQWN0aXZlKGl0ZW0uaHJlZik7'
    'CiAgICAgICAgICAgIHJldHVybiAoCiAgICAgICAgICAgICAgPExpbmsKICAgICAgICAgICAgICAg'
    'IGtleT17aXRlbS5ocmVmfQogICAgICAgICAgICAgICAgaHJlZj17aXRlbS5ocmVmfQogICAgICAg'
    'ICAgICAgICAgc3R5bGU9e3sKICAgICAgICAgICAgICAgICAgcGFkZGluZzogJzZweCAxMnB4JywK'
    'ICAgICAgICAgICAgICAgICAgYm9yZGVyUmFkaXVzOiA4LAogICAgICAgICAgICAgICAgICB0ZXh0'
    'RGVjb3JhdGlvbjogJ25vbmUnLAogICAgICAgICAgICAgICAgICBmb250U2l6ZTogMTMuNSwKICAg'
    'ICAgICAgICAgICAgICAgZm9udFdlaWdodDogYWN0aXZlID8gNjAwIDogNTAwLAogICAgICAgICAg'
    'ICAgICAgICBjb2xvcjogYWN0aXZlID8gJ3ZhcigtLWluayknIDogJ3ZhcigtLW11dGVkKScsCiAg'
    'ICAgICAgICAgICAgICAgIGJhY2tncm91bmQ6IGFjdGl2ZSA/ICd2YXIoLS1iZy1zb2Z0KScgOiAn'
    'dHJhbnNwYXJlbnQnLAogICAgICAgICAgICAgICAgICB3aGl0ZVNwYWNlOiAnbm93cmFwJywKICAg'
    'ICAgICAgICAgICAgICAgbGV0dGVyU3BhY2luZzogJy0wLjAwNWVtJywKICAgICAgICAgICAgICAg'
    'ICAgdHJhbnNpdGlvbjogJ2NvbG9yIDAuMTRzLCBiYWNrZ3JvdW5kIDAuMTRzJywKICAgICAgICAg'
    'ICAgICAgIH19CiAgICAgICAgICAgICAgPgogICAgICAgICAgICAgICAge2l0ZW0ubGFiZWx9CiAg'
    'ICAgICAgICAgICAgPC9MaW5rPgogICAgICAgICAgICApOwogICAgICAgICAgfSl9CiAgICAgICAg'
    'PC9uYXY+CgogICAgICAgIHsvKiBSaWdodCBjbHVzdGVyIOKAlCBkZXNrdG9wICovfQogICAgICAg'
    'IDxkaXYKICAgICAgICAgIGNsYXNzTmFtZT0idG9wYmFyLXJpZ2h0LWRlc2t0b3AiCiAgICAgICAg'
    'ICBzdHlsZT17ewogICAgICAgICAgICBkaXNwbGF5OiAnZmxleCcsCiAgICAgICAgICAgIGFsaWdu'
    'SXRlbXM6ICdjZW50ZXInLAogICAgICAgICAgICBnYXA6IDEwLAogICAgICAgICAgICBmbGV4U2hy'
    'aW5rOiAwLAogICAgICAgICAgfX0KICAgICAgICA+CiAgICAgICAgICA8c3BhbiBjbGFzc05hbWU9'
    'InBpbGwgcGlsbC1zaW0iIHRpdGxlPSJEYWRvcyBzaW11bGFkb3MgYXTDqSBpbnN0YWxhw6fDo28g'
    'ZsOtc2ljYSAxMeKAkzEyIEp1bmhvIDIwMjYiPgogICAgICAgICAgICBTSU1VTEFETwogICAgICAg'
    'ICAgPC9zcGFuPgogICAgICAgICAgPHNwYW4KICAgICAgICAgICAgY2xhc3NOYW1lPSJtb25vIgog'
    'ICAgICAgICAgICBzdHlsZT17ewogICAgICAgICAgICAgIGZvbnRTaXplOiAxMS41LAogICAgICAg'
    'ICAgICAgIGNvbG9yOiAndmFyKC0tZmFpbnQpJywKICAgICAgICAgICAgICBtaW5XaWR0aDogNjQs'
    'CiAgICAgICAgICAgICAgdGV4dEFsaWduOiAncmlnaHQnLAogICAgICAgICAgICAgIGZvbnRWYXJp'
    'YW50TnVtZXJpYzogJ3RhYnVsYXItbnVtcycsCiAgICAgICAgICAgIH19CiAgICAgICAgICA+CiAg'
    'ICAgICAgICAgIHt0aW1lfQogICAgICAgICAgPC9zcGFuPgogICAgICAgIDwvZGl2PgoKICAgICAg'
    'ICB7LyogSEFNQlVSR0VSIG1vYmlsZSAoZXNjb25kaWRvIGVtIGRlc2t0b3ApICovfQogICAgICAg'
    'IDxidXR0b24KICAgICAgICAgIGNsYXNzTmFtZT0idG9wYmFyLWJ1cmdlciIKICAgICAgICAgIG9u'
    'Q2xpY2s9eygpID0+IHNldE1vYmlsZU9wZW4oIW1vYmlsZU9wZW4pfQogICAgICAgICAgYXJpYS1s'
    'YWJlbD17bW9iaWxlT3BlbiA/ICdGZWNoYXIgbWVudScgOiAnQWJyaXIgbWVudSd9CiAgICAgICAg'
    'ICBhcmlhLWV4cGFuZGVkPXttb2JpbGVPcGVufQogICAgICAgICAgc3R5bGU9e3sKICAgICAgICAg'
    'ICAgZGlzcGxheTogJ25vbmUnLAogICAgICAgICAgICB3aWR0aDogNDIsCiAgICAgICAgICAgIGhl'
    'aWdodDogNDIsCiAgICAgICAgICAgIGJhY2tncm91bmQ6ICd0cmFuc3BhcmVudCcsCiAgICAgICAg'
    'ICAgIGJvcmRlcjogJzFweCBzb2xpZCB2YXIoLS1ib3JkZXItc3Ryb25nKScsCiAgICAgICAgICAg'
    'IGJvcmRlclJhZGl1czogMTAsCiAgICAgICAgICAgIGN1cnNvcjogJ3BvaW50ZXInLAogICAgICAg'
    'ICAgICBjb2xvcjogJ3ZhcigtLWluayknLAogICAgICAgICAgICBhbGlnbkl0ZW1zOiAnY2VudGVy'
    'JywKICAgICAgICAgICAganVzdGlmeUNvbnRlbnQ6ICdjZW50ZXInLAogICAgICAgICAgICBmbGV4'
    'U2hyaW5rOiAwLAogICAgICAgICAgICBwYWRkaW5nOiAwLAogICAgICAgICAgfX0KICAgICAgICA+'
    'CiAgICAgICAgICB7bW9iaWxlT3BlbiA/ICgKICAgICAgICAgICAgPHN2ZyB3aWR0aD0iMjAiIGhl'
    'aWdodD0iMjAiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSJjdXJyZW50'
    'Q29sb3IiIHN0cm9rZVdpZHRoPSIyIiBzdHJva2VMaW5lY2FwPSJyb3VuZCIgc3Ryb2tlTGluZWpv'
    'aW49InJvdW5kIj48bGluZSB4MT0iMTgiIHkxPSI2IiB4Mj0iNiIgeTI9IjE4Ii8+PGxpbmUgeDE9'
    'IjYiIHkxPSI2IiB4Mj0iMTgiIHkyPSIxOCIvPjwvc3ZnPgogICAgICAgICAgKSA6ICgKICAgICAg'
    'ICAgICAgPHN2ZyB3aWR0aD0iMjAiIGhlaWdodD0iMjAiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmls'
    'bD0ibm9uZSIgc3Ryb2tlPSJjdXJyZW50Q29sb3IiIHN0cm9rZVdpZHRoPSIyIiBzdHJva2VMaW5l'
    'Y2FwPSJyb3VuZCIgc3Ryb2tlTGluZWpvaW49InJvdW5kIj48bGluZSB4MT0iMyIgeTE9IjYiIHgy'
    'PSIyMSIgeTI9IjYiLz48bGluZSB4MT0iMyIgeTE9IjEyIiB4Mj0iMjEiIHkyPSIxMiIvPjxsaW5l'
    'IHgxPSIzIiB5MT0iMTgiIHgyPSIyMSIgeTI9IjE4Ii8+PC9zdmc+CiAgICAgICAgICApfQogICAg'
    'ICAgIDwvYnV0dG9uPgogICAgICA8L2hlYWRlcj4KCiAgICAgIHsvKiBNT0JJTEUgRFJBV0VSIGZ1'
    'bGxzY3JlZW4gKi99CiAgICAgIHttb2JpbGVPcGVuICYmICgKICAgICAgICA8ZGl2CiAgICAgICAg'
    'ICBjbGFzc05hbWU9InRvcGJhci1kcmF3ZXIiCiAgICAgICAgICBzdHlsZT17ewogICAgICAgICAg'
    'ICBwb3NpdGlvbjogJ2ZpeGVkJywKICAgICAgICAgICAgdG9wOiAndmFyKC0taGVhZGVyLWgsIDcy'
    'cHgpJywKICAgICAgICAgICAgbGVmdDogMCwKICAgICAgICAgICAgcmlnaHQ6IDAsCiAgICAgICAg'
    'ICAgIGJvdHRvbTogMCwKICAgICAgICAgICAgYmFja2dyb3VuZDogJ3doaXRlJywKICAgICAgICAg'
    'ICAgekluZGV4OiA5OSwKICAgICAgICAgICAgb3ZlcmZsb3dZOiAnYXV0bycsCiAgICAgICAgICAg'
    'IGRpc3BsYXk6ICdmbGV4JywKICAgICAgICAgICAgZmxleERpcmVjdGlvbjogJ2NvbHVtbicsCiAg'
    'ICAgICAgICAgIHBhZGRpbmc6ICcyMHB4IDE4cHggNDBweCcsCiAgICAgICAgICB9fQogICAgICAg'
    'ID4KICAgICAgICAgIHsvKiBTdGF0dXMgcGlsbCBubyB0b3BvIGRvIGRyYXdlciAqL30KICAgICAg'
    'ICAgIDxkaXYgc3R5bGU9e3sKICAgICAgICAgICAgZGlzcGxheTogJ2ZsZXgnLAogICAgICAgICAg'
    'ICBhbGlnbkl0ZW1zOiAnY2VudGVyJywKICAgICAgICAgICAganVzdGlmeUNvbnRlbnQ6ICdzcGFj'
    'ZS1iZXR3ZWVuJywKICAgICAgICAgICAgZ2FwOiAxMCwKICAgICAgICAgICAgcGFkZGluZ0JvdHRv'
    'bTogMTYsCiAgICAgICAgICAgIG1hcmdpbkJvdHRvbTogMTYsCiAgICAgICAgICAgIGJvcmRlckJv'
    'dHRvbTogJzFweCBzb2xpZCB2YXIoLS1ib3JkZXIpJywKICAgICAgICAgIH19PgogICAgICAgICAg'
    'ICA8c3BhbiBjbGFzc05hbWU9InBpbGwgcGlsbC1zaW0iPlNJTVVMQURPPC9zcGFuPgogICAgICAg'
    'ICAgICA8c3BhbiBjbGFzc05hbWU9Im1vbm8iIHN0eWxlPXt7IGZvbnRTaXplOiAxMiwgY29sb3I6'
    'ICd2YXIoLS1mYWludCknIH19Pnt0aW1lfTwvc3Bhbj4KICAgICAgICAgIDwvZGl2PgoKICAgICAg'
    'ICAgIHsvKiBMaW5rcyBncmFuZGVzICovfQogICAgICAgICAgPG5hdiBzdHlsZT17eyBkaXNwbGF5'
    'OiAnZmxleCcsIGZsZXhEaXJlY3Rpb246ICdjb2x1bW4nIH19PgogICAgICAgICAgICB7TkFWLm1h'
    'cCgoaXRlbSkgPT4gewogICAgICAgICAgICAgIGNvbnN0IGFjdGl2ZSA9IGlzQWN0aXZlKGl0ZW0u'
    'aHJlZik7CiAgICAgICAgICAgICAgcmV0dXJuICgKICAgICAgICAgICAgICAgIDxMaW5rCiAgICAg'
    'ICAgICAgICAgICAgIGtleT17aXRlbS5ocmVmfQogICAgICAgICAgICAgICAgICBocmVmPXtpdGVt'
    'LmhyZWZ9CiAgICAgICAgICAgICAgICAgIG9uQ2xpY2s9eygpID0+IHNldE1vYmlsZU9wZW4oZmFs'
    'c2UpfQogICAgICAgICAgICAgICAgICBzdHlsZT17ewogICAgICAgICAgICAgICAgICAgIGRpc3Bs'
    'YXk6ICdmbGV4JywKICAgICAgICAgICAgICAgICAgICBhbGlnbkl0ZW1zOiAnY2VudGVyJywKICAg'
    'ICAgICAgICAgICAgICAgICBqdXN0aWZ5Q29udGVudDogJ3NwYWNlLWJldHdlZW4nLAogICAgICAg'
    'ICAgICAgICAgICAgIHBhZGRpbmc6ICcxOHB4IDRweCcsCiAgICAgICAgICAgICAgICAgICAgZm9u'
    'dFNpemU6IDIyLAogICAgICAgICAgICAgICAgICAgIGZvbnRXZWlnaHQ6IGFjdGl2ZSA/IDYwMCA6'
    'IDUwMCwKICAgICAgICAgICAgICAgICAgICBjb2xvcjogYWN0aXZlID8gJ3ZhcigtLWluayknIDog'
    'J3ZhcigtLW11dGVkKScsCiAgICAgICAgICAgICAgICAgICAgdGV4dERlY29yYXRpb246ICdub25l'
    'JywKICAgICAgICAgICAgICAgICAgICBib3JkZXJCb3R0b206ICcxcHggc29saWQgdmFyKC0tYm9y'
    'ZGVyKScsCiAgICAgICAgICAgICAgICAgICAgbGV0dGVyU3BhY2luZzogJy0wLjAxNWVtJywKICAg'
    'ICAgICAgICAgICAgICAgICBmb250RmFtaWx5OiAndmFyKC0tZm9udC1kaXNwbGF5LCBJbnRlciwg'
    'c2Fucy1zZXJpZiknLAogICAgICAgICAgICAgICAgICB9fQogICAgICAgICAgICAgICAgPgogICAg'
    'ICAgICAgICAgICAgICA8c3Bhbj57aXRlbS5sYWJlbH08L3NwYW4+CiAgICAgICAgICAgICAgICAg'
    'IHthY3RpdmUgJiYgKAogICAgICAgICAgICAgICAgICAgIDxzcGFuIHN0eWxlPXt7CiAgICAgICAg'
    'ICAgICAgICAgICAgICB3aWR0aDogNiwgaGVpZ2h0OiA2LCBib3JkZXJSYWRpdXM6ICc1MCUnLAog'
    'ICAgICAgICAgICAgICAgICAgICAgYmFja2dyb3VuZDogJ3ZhcigtLWdyZWVuLWRhcmssICMxQjNB'
    'MjEpJywKICAgICAgICAgICAgICAgICAgICB9fSAvPgogICAgICAgICAgICAgICAgICApfQogICAg'
    'ICAgICAgICAgICAgPC9MaW5rPgogICAgICAgICAgICAgICk7CiAgICAgICAgICAgIH0pfQogICAg'
    'ICAgICAgPC9uYXY+CgogICAgICAgICAgey8qIEZvb3RlciBkbyBkcmF3ZXIgKi99CiAgICAgICAg'
    'ICA8ZGl2IHN0eWxlPXt7CiAgICAgICAgICAgIG1hcmdpblRvcDogJ2F1dG8nLAogICAgICAgICAg'
    'ICBwYWRkaW5nVG9wOiAyNCwKICAgICAgICAgICAgZm9udFNpemU6IDExLAogICAgICAgICAgICBj'
    'b2xvcjogJ3ZhcigtLW11dGVkKScsCiAgICAgICAgICAgIGZvbnRGYW1pbHk6ICd2YXIoLS1mb250'
    'LW1vbm8pJywKICAgICAgICAgICAgbGV0dGVyU3BhY2luZzogJzAuMDRlbScsCiAgICAgICAgICB9'
    'fT4KICAgICAgICAgICAgw5cgUm9jayBpbiBSaW8gTGlzYm9hIDIwMjYgwrcgUGFycXVlIFRlam8g'
    'wrcgMjDigJMyOCBKdW4KICAgICAgICAgIDwvZGl2PgogICAgICAgIDwvZGl2PgogICAgICApfQoK'
    'ICAgICAgPHN0eWxlIGpzeCBnbG9iYWw+e2AKICAgICAgICAudG9wYmFyLW5hdi1kZXNrdG9wOjot'
    'd2Via2l0LXNjcm9sbGJhciB7IGRpc3BsYXk6IG5vbmU7IH0KICAgICAgICAKICAgICAgICAvKiBN'
    'b2JpbGUgYnJlYWtwb2ludCAqLwogICAgICAgIEBtZWRpYSAobWF4LXdpZHRoOiA5MjBweCkgewog'
    'ICAgICAgICAgLnRvcGJhci1uYXYtZGVza3RvcCB7IGRpc3BsYXk6IG5vbmUgIWltcG9ydGFudDsg'
    'fQogICAgICAgICAgLnRvcGJhci1yaWdodC1kZXNrdG9wIHsgZGlzcGxheTogbm9uZSAhaW1wb3J0'
    'YW50OyB9CiAgICAgICAgICAudG9wYmFyLWJ1cmdlciB7IGRpc3BsYXk6IGZsZXggIWltcG9ydGFu'
    'dDsgfQogICAgICAgIH0KCiAgICAgICAgLyogUGhvbmUgcGVxdWVubyDigJQgYnJhbmQgYWJyZXZp'
    'YWRhIHZpYSBlbGxpcHNpcyBzZSBuZWNlc3PDoXJpbyAqLwogICAgICAgIEBtZWRpYSAobWF4LXdp'
    'ZHRoOiAzODBweCkgewogICAgICAgICAgLnRvcGJhci1icmFuZCB7CiAgICAgICAgICAgIGZvbnQt'
    'c2l6ZTogMTNweCAhaW1wb3J0YW50OwogICAgICAgICAgICBtYXgtd2lkdGg6IDEzMHB4ICFpbXBv'
    'cnRhbnQ7CiAgICAgICAgICB9CiAgICAgICAgfQogICAgICBgfTwvc3R5bGU+CiAgICA8Lz4KICAp'
    'Owp9Cg=='
)

def run(cmd, cwd=None):
    print(f"$ {cmd}")
    r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if r.stdout.strip(): print(r.stdout.rstrip())
    if r.stderr.strip(): print(r.stderr.rstrip(), file=sys.stderr)
    return r.returncode == 0

def main():
    root = Path.cwd()
    tb = root / "frontend" / "components" / "v2" / "TopBar.tsx"
    if not tb.exists():
        print("ERRO: TopBar.tsx não encontrado"); sys.exit(1)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(tb, tb.with_suffix(f".tsx.bak.v14.{stamp}"))
    data = base64.b64decode("".join(TOPBAR_B64))
    tb.write_bytes(data)
    print(f"  OK TopBar.tsx · {len(data)} B")
    print(f"  OK hamburger + drawer fullscreen activos abaixo de 920px")
    
    run("git add frontend/components/v2/TopBar.tsx", cwd=str(root))
    run('git commit -m "feat(v14): mobile menu hamburger + drawer fullscreen para todas as páginas"', cwd=str(root))
    run("git push", cwd=str(root))
    
    print("")
    print("  Aguarda ~90s. Teste:")
    print("    1. Desktop: vê nav linha como antes")
    print("    2. Mobile real (telemóvel): vês HAMBURGER no canto direito")
    print("    3. Clica no hamburger → abre drawer fullscreen com 9 links")
    print("    4. Click num link → naviga + fecha drawer automaticamente")
    print("")
    print("  Para forçar refresh em telemóvel iOS:")
    print("    Settings → Safari → Clear History and Website Data")
    print("  Ou abre em browser anónimo / em modo de leitura no PC com DevTools.")

if __name__ == "__main__":
    main()

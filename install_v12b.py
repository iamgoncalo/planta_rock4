#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
install_v12b — HOTFIX build error

Erro: useSearchParams() should be wrapped in a suspense boundary at page "/v2/chat"
Fix: separar componente em ChatInner + Suspense wrapper
"""

import base64, os, shutil, subprocess, sys
from datetime import datetime
from pathlib import Path

os.environ["PATH"] = ":".join([
    "/usr/bin", "/bin", "/usr/sbin", "/sbin",
    "/usr/local/bin", "/opt/homebrew/bin",
    os.environ.get("PATH", ""),])

CHAT_B64 = (
    'J3VzZSBjbGllbnQnOwoKaW1wb3J0IHsgU3VzcGVuc2UsIHVzZUVmZmVjdCwgdXNlUmVmLCB1c2VT'
    'dGF0ZSB9IGZyb20gJ3JlYWN0JzsKaW1wb3J0IHsgdXNlUm91dGVyLCB1c2VTZWFyY2hQYXJhbXMg'
    'fSBmcm9tICduZXh0L25hdmlnYXRpb24nOwoKY29uc3QgQVBJX0JBU0UgPSBwcm9jZXNzLmVudi5O'
    'RVhUX1BVQkxJQ19BUElfQkFTRSB8fCAnaHR0cHM6Ly9hcGkucGxhbnRhcm9ja2lucmlvLmNvbSc7'
    'CmNvbnN0IFNUT1JBR0VfS0VZID0gJ3BsYW50YS1jaGF0LWhpc3RvcnktdjEnOwoKaW50ZXJmYWNl'
    'IE1zZyB7CiAgcm9sZTogJ3VzZXInIHwgJ2Fzc2lzdGFudCc7CiAgY29udGVudDogc3RyaW5nOwog'
    'IHRzOiBudW1iZXI7Cn0KCmZ1bmN0aW9uIGxvYWRIaXN0b3J5KCk6IE1zZ1tdIHsKICBpZiAodHlw'
    'ZW9mIHdpbmRvdyA9PT0gJ3VuZGVmaW5lZCcpIHJldHVybiBbXTsKICB0cnkgewogICAgY29uc3Qg'
    'cmF3ID0gbG9jYWxTdG9yYWdlLmdldEl0ZW0oU1RPUkFHRV9LRVkpOwogICAgaWYgKCFyYXcpIHJl'
    'dHVybiBbXTsKICAgIGNvbnN0IHBhcnNlZCA9IEpTT04ucGFyc2UocmF3KTsKICAgIGlmIChBcnJh'
    'eS5pc0FycmF5KHBhcnNlZCkpIHJldHVybiBwYXJzZWQ7CiAgICByZXR1cm4gW107CiAgfSBjYXRj'
    'aCB7CiAgICByZXR1cm4gW107CiAgfQp9CgpmdW5jdGlvbiBzYXZlSGlzdG9yeShtc2dzOiBNc2db'
    'XSkgewogIGlmICh0eXBlb2Ygd2luZG93ID09PSAndW5kZWZpbmVkJykgcmV0dXJuOwogIHRyeSB7'
    'CiAgICBsb2NhbFN0b3JhZ2Uuc2V0SXRlbShTVE9SQUdFX0tFWSwgSlNPTi5zdHJpbmdpZnkobXNn'
    'cy5zbGljZSgtMjAwKSkpOwogIH0gY2F0Y2gge30KfQoKLy8gSW5uZXIgY29tcG9uZW50IHF1ZSBV'
    'U0EgdXNlU2VhcmNoUGFyYW1zIOKAlCB0ZW0gZGUgZXN0YXIgZGVudHJvIGRlIFN1c3BlbnNlCmZ1'
    'bmN0aW9uIENoYXRJbm5lcigpIHsKICBjb25zdCByb3V0ZXIgPSB1c2VSb3V0ZXIoKTsKICBjb25z'
    'dCBwYXJhbXMgPSB1c2VTZWFyY2hQYXJhbXMoKTsKICBjb25zdCBbbWVzc2FnZXMsIHNldE1lc3Nh'
    'Z2VzXSA9IHVzZVN0YXRlPE1zZ1tdPihbXSk7CiAgY29uc3QgW2lucHV0LCBzZXRJbnB1dF0gPSB1'
    'c2VTdGF0ZSgnJyk7CiAgY29uc3QgW3NlbmRpbmcsIHNldFNlbmRpbmddID0gdXNlU3RhdGUoZmFs'
    'c2UpOwogIGNvbnN0IHNjcm9sbFJlZiA9IHVzZVJlZjxIVE1MRGl2RWxlbWVudD4obnVsbCk7CiAg'
    'Y29uc3QgaGFuZGxlZFF1ZXJ5ID0gdXNlUmVmPHN0cmluZyB8IG51bGw+KG51bGwpOwoKICB1c2VF'
    'ZmZlY3QoKCkgPT4gewogICAgc2V0TWVzc2FnZXMobG9hZEhpc3RvcnkoKSk7CiAgfSwgW10pOwoK'
    'ICB1c2VFZmZlY3QoKCkgPT4gewogICAgaWYgKHNjcm9sbFJlZi5jdXJyZW50KSB7CiAgICAgIHNj'
    'cm9sbFJlZi5jdXJyZW50LnNjcm9sbFRvcCA9IHNjcm9sbFJlZi5jdXJyZW50LnNjcm9sbEhlaWdo'
    'dDsKICAgIH0KICB9LCBbbWVzc2FnZXNdKTsKCiAgdXNlRWZmZWN0KCgpID0+IHsKICAgIGNvbnN0'
    'IHEgPSBwYXJhbXM/LmdldCgncScpOwogICAgaWYgKHEgJiYgaGFuZGxlZFF1ZXJ5LmN1cnJlbnQg'
    'IT09IHEpIHsKICAgICAgaGFuZGxlZFF1ZXJ5LmN1cnJlbnQgPSBxOwogICAgICBzZW5kKHEpOwog'
    'ICAgICByb3V0ZXIucmVwbGFjZSgnL3YyL2NoYXQnLCB7IHNjcm9sbDogZmFsc2UgfSk7CiAgICB9'
    'CiAgLy8gZXNsaW50LWRpc2FibGUtbmV4dC1saW5lIHJlYWN0LWhvb2tzL2V4aGF1c3RpdmUtZGVw'
    'cwogIH0sIFtwYXJhbXNdKTsKCiAgY29uc3Qgc2VuZCA9IGFzeW5jICh0ZXh0Pzogc3RyaW5nKSA9'
    'PiB7CiAgICBjb25zdCBjb250ZW50ID0gKHRleHQgPz8gaW5wdXQpLnRyaW0oKTsKICAgIGlmICgh'
    'Y29udGVudCB8fCBzZW5kaW5nKSByZXR1cm47CiAgICBjb25zdCB1c2VyTXNnOiBNc2cgPSB7IHJv'
    'bGU6ICd1c2VyJywgY29udGVudCwgdHM6IERhdGUubm93KCkgfTsKICAgIHNldE1lc3NhZ2VzKCht'
    'KSA9PiB7CiAgICAgIGNvbnN0IG5leHQgPSBbLi4ubSwgdXNlck1zZ107CiAgICAgIHNhdmVIaXN0'
    'b3J5KG5leHQpOwogICAgICByZXR1cm4gbmV4dDsKICAgIH0pOwogICAgc2V0SW5wdXQoJycpOwog'
    'ICAgc2V0U2VuZGluZyh0cnVlKTsKCiAgICB0cnkgewogICAgICBjb25zdCByID0gYXdhaXQgZmV0'
    'Y2goYCR7QVBJX0JBU0V9L2FwaS92MS9jaGF0YCwgewogICAgICAgIG1ldGhvZDogJ1BPU1QnLAog'
    'ICAgICAgIGhlYWRlcnM6IHsgJ2NvbnRlbnQtdHlwZSc6ICdhcHBsaWNhdGlvbi9qc29uJyB9LAog'
    'ICAgICAgIGJvZHk6IEpTT04uc3RyaW5naWZ5KHsgbWVzc2FnZTogY29udGVudCB9KSwKICAgICAg'
    'fSk7CiAgICAgIGxldCByZXBseSA9ICdEZXNjdWxwYSwgbsOjbyBjb25zZWd1aSBwcm9jZXNzYXIu'
    'JzsKICAgICAgaWYgKHIub2spIHsKICAgICAgICBjb25zdCBqID0gYXdhaXQgci5qc29uKCk7CiAg'
    'ICAgICAgcmVwbHkgPSBqLnJlcGx5IHx8IGoubWVzc2FnZSB8fCBqLnJlc3BvbnNlIHx8IGoudGV4'
    'dCB8fCBKU09OLnN0cmluZ2lmeShqKS5zbGljZSgwLCAyMDApOwogICAgICB9IGVsc2UgewogICAg'
    'ICAgIHJlcGx5ID0gYEVycm8gZG8gc2Vydmlkb3IgKCR7ci5zdGF0dXN9KS5gOwogICAgICB9CiAg'
    'ICAgIGNvbnN0IGFpTXNnOiBNc2cgPSB7IHJvbGU6ICdhc3Npc3RhbnQnLCBjb250ZW50OiByZXBs'
    'eSwgdHM6IERhdGUubm93KCkgfTsKICAgICAgc2V0TWVzc2FnZXMoKG0pID0+IHsKICAgICAgICBj'
    'b25zdCBuZXh0ID0gWy4uLm0sIGFpTXNnXTsKICAgICAgICBzYXZlSGlzdG9yeShuZXh0KTsKICAg'
    'ICAgICByZXR1cm4gbmV4dDsKICAgICAgfSk7CiAgICB9IGNhdGNoIChlKSB7CiAgICAgIGNvbnN0'
    'IGVyck1zZzogTXNnID0gewogICAgICAgIHJvbGU6ICdhc3Npc3RhbnQnLAogICAgICAgIGNvbnRl'
    'bnQ6ICdQcm9ibGVtYSBkZSBsaWdhw6fDo28uIFZlcmlmaWNhIGEgcmVkZS4nLAogICAgICAgIHRz'
    'OiBEYXRlLm5vdygpLAogICAgICB9OwogICAgICBzZXRNZXNzYWdlcygobSkgPT4gewogICAgICAg'
    'IGNvbnN0IG5leHQgPSBbLi4ubSwgZXJyTXNnXTsKICAgICAgICBzYXZlSGlzdG9yeShuZXh0KTsK'
    'ICAgICAgICByZXR1cm4gbmV4dDsKICAgICAgfSk7CiAgICB9IGZpbmFsbHkgewogICAgICBzZXRT'
    'ZW5kaW5nKGZhbHNlKTsKICAgIH0KICB9OwoKICBjb25zdCBjbGVhckhpc3RvcnkgPSAoKSA9PiB7'
    'CiAgICBpZiAoY29uZmlybSgnTGltcGFyIHRvZG8gbyBoaXN0w7NyaWNvIGRlIGNvbnZlcnNhPycp'
    'KSB7CiAgICAgIHNldE1lc3NhZ2VzKFtdKTsKICAgICAgc2F2ZUhpc3RvcnkoW10pOwogICAgfQog'
    'IH07CgogIHJldHVybiAoCiAgICA8ZGl2IGNsYXNzTmFtZT0icGFnZSIgc3R5bGU9e3sgbWF4V2lk'
    'dGg6IDgyMCwgcGFkZGluZ0JvdHRvbTogMzIgfX0+CiAgICAgIDxkaXYKICAgICAgICBzdHlsZT17'
    'ewogICAgICAgICAgZGlzcGxheTogJ2ZsZXgnLAogICAgICAgICAganVzdGlmeUNvbnRlbnQ6ICdz'
    'cGFjZS1iZXR3ZWVuJywKICAgICAgICAgIGFsaWduSXRlbXM6ICdmbGV4LWVuZCcsCiAgICAgICAg'
    'ICBtYXJnaW5Cb3R0b206IDI0LAogICAgICAgICAgYm9yZGVyQm90dG9tOiAnMXB4IHNvbGlkIHZh'
    'cigtLWJvcmRlciknLAogICAgICAgICAgcGFkZGluZ0JvdHRvbTogMTgsCiAgICAgICAgfX0KICAg'
    'ICAgPgogICAgICAgIDxkaXY+CiAgICAgICAgICA8ZGl2IGNsYXNzTmFtZT0ic2VjdGlvbi1sYWJl'
    'bCI+Q2hhdCDCtyBQbGFudGEgU21hcnQgSG9tZXM8L2Rpdj4KICAgICAgICAgIDxoMgogICAgICAg'
    'ICAgICBzdHlsZT17ewogICAgICAgICAgICAgIGZvbnRGYW1pbHk6ICd2YXIoLS1mb250LWRpc3Bs'
    'YXkpJywKICAgICAgICAgICAgICBmb250U2l6ZTogJ2NsYW1wKDI4cHgsIDR2dywgNDRweCknLAog'
    'ICAgICAgICAgICAgIGZvbnRXZWlnaHQ6IDUwMCwKICAgICAgICAgICAgICBsZXR0ZXJTcGFjaW5n'
    'OiAnLTAuMDNlbScsCiAgICAgICAgICAgICAgbGluZUhlaWdodDogMSwKICAgICAgICAgICAgICBt'
    'YXJnaW5Ub3A6IDYsCiAgICAgICAgICAgIH19CiAgICAgICAgICA+CiAgICAgICAgICAgIEFzayBQ'
    'bGFudGEgYW55dGhpbmcKICAgICAgICAgIDwvaDI+CiAgICAgICAgPC9kaXY+CiAgICAgICAge21l'
    'c3NhZ2VzLmxlbmd0aCA+IDAgJiYgKAogICAgICAgICAgPGJ1dHRvbgogICAgICAgICAgICBvbkNs'
    'aWNrPXtjbGVhckhpc3Rvcnl9CiAgICAgICAgICAgIHN0eWxlPXt7CiAgICAgICAgICAgICAgYmFj'
    'a2dyb3VuZDogJ3RyYW5zcGFyZW50JywKICAgICAgICAgICAgICBib3JkZXI6ICcxcHggc29saWQg'
    'dmFyKC0tYm9yZGVyLXN0cm9uZyknLAogICAgICAgICAgICAgIGJvcmRlclJhZGl1czogOTk5LAog'
    'ICAgICAgICAgICAgIHBhZGRpbmc6ICc2cHggMTRweCcsCiAgICAgICAgICAgICAgZm9udFNpemU6'
    'IDEyLAogICAgICAgICAgICAgIGNvbG9yOiAndmFyKC0tbXV0ZWQpJywKICAgICAgICAgICAgICBj'
    'dXJzb3I6ICdwb2ludGVyJywKICAgICAgICAgICAgfX0KICAgICAgICAgID4KICAgICAgICAgICAg'
    'TGltcGFyIGhpc3TDs3JpY28KICAgICAgICAgIDwvYnV0dG9uPgogICAgICAgICl9CiAgICAgIDwv'
    'ZGl2PgoKICAgICAge21lc3NhZ2VzLmxlbmd0aCA9PT0gMCAmJiAoCiAgICAgICAgPGRpdiBzdHls'
    'ZT17eyBwYWRkaW5nOiAnNDBweCAwIDIwcHgnLCBjb2xvcjogJ3ZhcigtLW11dGVkKScgfX0+CiAg'
    'ICAgICAgICA8cCBzdHlsZT17eyBmb250U2l6ZTogMTcsIGxpbmVIZWlnaHQ6IDEuNTUsIG1heFdp'
    'ZHRoOiA1NjAsIG1hcmdpbkJvdHRvbTogMTggfX0+CiAgICAgICAgICAgIFNvdSBvIGFzc2lzdGVu'
    'dGUgZGEgUGxhbnRhIFNtYXJ0IEhvbWVzLiBQZXJndW50YS1tZSBzb2JyZSBjbHVzdGVycywgb2N1'
    'cGHDp8OjbywKICAgICAgICAgICAgbGltcGV6YSwgZXF1aXBhcywgc2Vuc29yZXMgb3UgcXVhbHF1'
    'ZXIgY29pc2EgZG8gZmVzdGl2YWwuCiAgICAgICAgICA8L3A+CiAgICAgICAgICA8ZGl2IHN0eWxl'
    'PXt7IGRpc3BsYXk6ICdmbGV4JywgZmxleFdyYXA6ICd3cmFwJywgZ2FwOiA2IH19PgogICAgICAg'
    'ICAgICB7WwogICAgICAgICAgICAgICdRdWFsIG8gY2x1c3RlciBtYWlzIGNoZWlvIGFnb3JhPycs'
    'CiAgICAgICAgICAgICAgJ1F1ZW0gZXN0w6EgYSBsaW1wYXIgbyBXQy0wND8nLAogICAgICAgICAg'
    'ICAgICdRdWFuZG8gw6kgYSBwcsOzeGltYSBsaW1wZXphPycsCiAgICAgICAgICAgICAgJ1F1YW50'
    'YXMgcGVzc29hcyBow6EgYWdvcmEgbm8gZmVzdGl2YWw/JywKICAgICAgICAgICAgXS5tYXAoKHMp'
    'ID0+ICgKICAgICAgICAgICAgICA8YnV0dG9uCiAgICAgICAgICAgICAgICBrZXk9e3N9CiAgICAg'
    'ICAgICAgICAgICBvbkNsaWNrPXsoKSA9PiBzZW5kKHMpfQogICAgICAgICAgICAgICAgc3R5bGU9'
    'e3sKICAgICAgICAgICAgICAgICAgYmFja2dyb3VuZDogJ3ZhcigtLWJnLXNvZnQpJywKICAgICAg'
    'ICAgICAgICAgICAgYm9yZGVyOiAnMXB4IHNvbGlkIHZhcigtLWJvcmRlciknLAogICAgICAgICAg'
    'ICAgICAgICBib3JkZXJSYWRpdXM6IDk5OSwKICAgICAgICAgICAgICAgICAgcGFkZGluZzogJzdw'
    'eCAxM3B4JywKICAgICAgICAgICAgICAgICAgZm9udFNpemU6IDEyLjUsCiAgICAgICAgICAgICAg'
    'ICAgIGN1cnNvcjogJ3BvaW50ZXInLAogICAgICAgICAgICAgICAgICBjb2xvcjogJ3ZhcigtLWlu'
    'ayknLAogICAgICAgICAgICAgICAgICBmb250RmFtaWx5OiAnaW5oZXJpdCcsCiAgICAgICAgICAg'
    'ICAgICB9fQogICAgICAgICAgICAgID4KICAgICAgICAgICAgICAgIHtzfQogICAgICAgICAgICAg'
    'IDwvYnV0dG9uPgogICAgICAgICAgICApKX0KICAgICAgICAgIDwvZGl2PgogICAgICAgIDwvZGl2'
    'PgogICAgICApfQoKICAgICAgPGRpdgogICAgICAgIHJlZj17c2Nyb2xsUmVmfQogICAgICAgIHN0'
    'eWxlPXt7CiAgICAgICAgICBkaXNwbGF5OiAnZmxleCcsCiAgICAgICAgICBmbGV4RGlyZWN0aW9u'
    'OiAnY29sdW1uJywKICAgICAgICAgIGdhcDogMTIsCiAgICAgICAgICBtYXJnaW5Cb3R0b206IDI0'
    'LAogICAgICAgICAgbWF4SGVpZ2h0OiAnY2FsYygxMDB2aCAtIDM2MHB4KScsCiAgICAgICAgICBv'
    'dmVyZmxvd1k6ICdhdXRvJywKICAgICAgICB9fQogICAgICA+CiAgICAgICAge21lc3NhZ2VzLm1h'
    'cCgobSwgaSkgPT4gKAogICAgICAgICAgPGRpdgogICAgICAgICAgICBrZXk9e2l9CiAgICAgICAg'
    'ICAgIHN0eWxlPXt7CiAgICAgICAgICAgICAgYWxpZ25TZWxmOiBtLnJvbGUgPT09ICd1c2VyJyA/'
    'ICdmbGV4LWVuZCcgOiAnZmxleC1zdGFydCcsCiAgICAgICAgICAgICAgYmFja2dyb3VuZDogbS5y'
    'b2xlID09PSAndXNlcicgPyAndmFyKC0taW5rKScgOiAnd2hpdGUnLAogICAgICAgICAgICAgIGNv'
    'bG9yOiBtLnJvbGUgPT09ICd1c2VyJyA/ICd3aGl0ZScgOiAndmFyKC0taW5rKScsCiAgICAgICAg'
    'ICAgICAgcGFkZGluZzogJzEycHggMTZweCcsCiAgICAgICAgICAgICAgYm9yZGVyUmFkaXVzOiAx'
    'NiwKICAgICAgICAgICAgICBtYXhXaWR0aDogJzg1JScsCiAgICAgICAgICAgICAgZm9udFNpemU6'
    'IDE1LAogICAgICAgICAgICAgIGxpbmVIZWlnaHQ6IDEuNTUsCiAgICAgICAgICAgICAgd2hpdGVT'
    'cGFjZTogJ3ByZS13cmFwJywKICAgICAgICAgICAgICBib3JkZXI6IG0ucm9sZSA9PT0gJ2Fzc2lz'
    'dGFudCcgPyAnMXB4IHNvbGlkIHZhcigtLWJvcmRlciknIDogJ25vbmUnLAogICAgICAgICAgICAg'
    'IGJveFNoYWRvdzogbS5yb2xlID09PSAnYXNzaXN0YW50JyA/ICd2YXIoLS1zaGFkb3ctc20pJyA6'
    'ICdub25lJywKICAgICAgICAgICAgfX0KICAgICAgICAgID4KICAgICAgICAgICAge20uY29udGVu'
    'dH0KICAgICAgICAgIDwvZGl2PgogICAgICAgICkpfQogICAgICAgIHtzZW5kaW5nICYmICgKICAg'
    'ICAgICAgIDxkaXYKICAgICAgICAgICAgc3R5bGU9e3sKICAgICAgICAgICAgICBhbGlnblNlbGY6'
    'ICdmbGV4LXN0YXJ0JywKICAgICAgICAgICAgICBiYWNrZ3JvdW5kOiAnd2hpdGUnLAogICAgICAg'
    'ICAgICAgIHBhZGRpbmc6ICcxMnB4IDE2cHgnLAogICAgICAgICAgICAgIGJvcmRlclJhZGl1czog'
    'MTYsCiAgICAgICAgICAgICAgYm9yZGVyOiAnMXB4IHNvbGlkIHZhcigtLWJvcmRlciknLAogICAg'
    'ICAgICAgICAgIGZvbnRTaXplOiAxMywKICAgICAgICAgICAgICBjb2xvcjogJ3ZhcigtLW11dGVk'
    'KScsCiAgICAgICAgICAgIH19CiAgICAgICAgICA+CiAgICAgICAgICAgIDxzcGFuIHN0eWxlPXt7'
    'IGFuaW1hdGlvbjogJ2RvdHMgMS40cyBpbmZpbml0ZScgfX0+4pePIOKXjyDil488L3NwYW4+CiAg'
    'ICAgICAgICA8L2Rpdj4KICAgICAgICApfQogICAgICA8L2Rpdj4KCiAgICAgIDxzdHlsZSBqc3g+'
    'e2AKICAgICAgICBAa2V5ZnJhbWVzIGRvdHMgewogICAgICAgICAgMCUsIDEwMCUgeyBvcGFjaXR5'
    'OiAwLjM7IH0KICAgICAgICAgIDUwJSB7IG9wYWNpdHk6IDE7IH0KICAgICAgICB9CiAgICAgIGB9'
    'PC9zdHlsZT4KICAgIDwvZGl2PgogICk7Cn0KCi8vIE91dGVyIGNvbXBvbmVudCDigJQgU3VzcGVu'
    'c2Ugd3JhcHBlciBleGlnaWRvIHBlbG8gTmV4dC5qcyAxNCBxdWFuZG8gc2UgdXNhIHVzZVNlYXJj'
    'aFBhcmFtcwpleHBvcnQgZGVmYXVsdCBmdW5jdGlvbiBDaGF0UGFnZSgpIHsKICByZXR1cm4gKAog'
    'ICAgPFN1c3BlbnNlCiAgICAgIGZhbGxiYWNrPXsKICAgICAgICA8ZGl2IGNsYXNzTmFtZT0icGFn'
    'ZSIgc3R5bGU9e3sgbWF4V2lkdGg6IDgyMCB9fT4KICAgICAgICAgIDxkaXYgY2xhc3NOYW1lPSJz'
    'ZWN0aW9uLWxhYmVsIj5DaGF0IMK3IGEgY2FycmVnYXIuLi48L2Rpdj4KICAgICAgICA8L2Rpdj4K'
    'ICAgICAgfQogICAgPgogICAgICA8Q2hhdElubmVyIC8+CiAgICA8L1N1c3BlbnNlPgogICk7Cn0K'
)

def run(cmd, cwd=None):
    print(f"$ {cmd}")
    r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if r.stdout.strip(): print(r.stdout.rstrip())
    if r.stderr.strip(): print(r.stderr.rstrip(), file=sys.stderr)
    return r.returncode == 0

def main():
    root = Path.cwd()
    if not (root / "frontend").exists():
        print("ERRO: corre a partir de ~/planta_rock4"); sys.exit(1)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    chat = root / "frontend" / "app" / "v2" / "chat" / "page.tsx"
    if chat.exists():
        shutil.copy2(chat, chat.with_suffix(f".tsx.bak.v12b.{stamp}"))
    data = base64.b64decode("".join(CHAT_B64))
    chat.write_bytes(data)
    print(f"  OK chat/page.tsx actualizado ({len(data)} B) com Suspense wrapper")
    
    run("git add frontend/app/v2/chat/page.tsx", cwd=str(root))
    run('git commit -m "fix(v12b): wrap useSearchParams in Suspense for build"', cwd=str(root))
    run("git push", cwd=str(root))
    
    print("")
    print("  Aguarda ~90s e CMD+SHIFT+R em https://www.plantarockinrio.com/v2")

if __name__ == "__main__":
    main()

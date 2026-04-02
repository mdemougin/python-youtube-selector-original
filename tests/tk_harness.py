"""Tk-free stubs so workout_gui tests run without Tcl/Tk (and mock ImageTk)."""

from __future__ import annotations

from unittest.mock import MagicMock


class DummyBooleanVar:
    def __init__(self, value: bool = True, master=None):
        self._value = value

    def get(self) -> bool:
        return self._value

    def set(self, value: bool) -> None:
        self._value = value


class DummyStringVar:
    def __init__(self, value: str = "", master=None):
        self._value = value

    def get(self) -> str:
        return self._value

    def set(self, value: str) -> None:
        self._value = value


class StatefulEntry:
    def __init__(self) -> None:
        self._text = ""

    def insert(self, index, string: str) -> None:
        self._text = string + self._text

    def delete(self, first, last=None) -> None:
        self._text = ""

    def get(self) -> str:
        return self._text


class StatefulLabel:
    def __init__(self) -> None:
        self._text = ""

    def config(self, **kw) -> None:
        if "text" in kw:
            self._text = kw["text"]

    def cget(self, key: str) -> str:
        if key == "text":
            return self._text
        return ""


class FakeCombobox:
    def __init__(self) -> None:
        self._values: tuple = ()
        self.pack = MagicMock()
        self.grid = MagicMock()
        self.bind = MagicMock()
        self.set = MagicMock()

    def __setitem__(self, key: str, value) -> None:
        if key == "values":
            self._values = tuple(value) if value is not None else ()

    def __getitem__(self, key: str):
        if key == "values":
            return self._values
        raise KeyError(key)


def _master_from_args(args, kwargs):
    if "master" in kwargs:
        return kwargs["master"]
    if args:
        return args[0]
    return None


def apply_workout_gui_tk_patches(mocker, root: MagicMock) -> FakeCombobox:
    """Patch workout_gui; root.after runs callbacks immediately. Returns shared combobox."""
    root.after = lambda _ms, cb: cb()
    root.update = MagicMock()
    root.title = MagicMock()
    root.geometry = MagicMock()
    root.columnconfigure = MagicMock()
    root.rowconfigure = MagicMock()
    root.bind_all = MagicMock()
    if not hasattr(root, "_children"):
        root._children = []

    mocker.patch("workout_gui.tk.BooleanVar", DummyBooleanVar)
    mocker.patch("workout_gui.tk.StringVar", DummyStringVar)
    mocker.patch("workout_gui.ImageTk.PhotoImage", return_value=MagicMock())

    shared_combo = FakeCombobox()

    def register_child(master, child):
        if master is not None:
            if not hasattr(master, "_children"):
                master._children = []
            master._children.append(child)

    def make_destroy(master, child):
        def _destroy():
            ch = getattr(master, "_children", None)
            if ch and child in ch:
                ch.remove(child)

        return _destroy

    def frame_factory(*args, **kwargs):
        master = _master_from_args(args, kwargs)
        w = MagicMock()
        w._children = []
        w.winfo_children = lambda self=w: list(self._children)
        w.grid = MagicMock()
        w.grid_remove = MagicMock()
        w.pack = MagicMock()
        w.pack_forget = MagicMock()
        w.bind = MagicMock()
        w.configure = MagicMock()
        w.config = MagicMock()
        w.columnconfigure = MagicMock()
        w.rowconfigure = MagicMock()
        w.cget = MagicMock(return_value="")
        w.create_window = MagicMock()
        w.bbox = MagicMock(return_value=(0, 0, 1, 1))
        w.destroy = MagicMock(side_effect=make_destroy(master, w))
        register_child(master, w)
        return w

    def ttk_label_factory(*args, **kwargs):
        sl = StatefulLabel()
        w = MagicMock()
        w.config = sl.config
        w.cget = sl.cget
        w.pack = MagicMock()
        w.grid = MagicMock()
        w.bind = MagicMock()
        w.winfo_children = MagicMock(return_value=[])
        return w

    def entry_factory(*args, **kwargs):
        se = StatefulEntry()
        w = MagicMock()
        w.insert = se.insert
        w.delete = se.delete
        w.get = se.get
        w.pack = MagicMock()
        w.grid = MagicMock()
        return w

    def combobox_factory(*args, **kwargs):
        return shared_combo

    mocker.patch("workout_gui.ttk.Frame", side_effect=frame_factory)
    mocker.patch("workout_gui.ttk.Label", side_effect=ttk_label_factory)
    mocker.patch("workout_gui.ttk.Button", side_effect=frame_factory)
    mocker.patch("workout_gui.ttk.Entry", side_effect=entry_factory)
    mocker.patch("workout_gui.ttk.Scrollbar", side_effect=frame_factory)
    mocker.patch("workout_gui.ttk.Combobox", side_effect=combobox_factory)
    mocker.patch("workout_gui.tk.Canvas", side_effect=frame_factory)
    mocker.patch("workout_gui.tk.Frame", side_effect=frame_factory)
    mocker.patch("workout_gui.tk.Label", side_effect=frame_factory)

    return shared_combo

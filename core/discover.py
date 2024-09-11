# -*- coding:utf-8 -*-
#  Copyright (c) 2016-present The ZLMediaKit project authors. All Rights Reserved.
#  This file is part of ZLMediaKit(https://github.com/ZLMediaKit/Github-AI-Assistant).
#  Use of this source code is governed by MIT-like license that can be found in the
#  LICENSE file in the root of the source tree. All contributing project authors
#  may be found in the AUTHORS file in the root of the source tree.
#

from glob import glob
from importlib import import_module, util
from inspect import getmembers
from pathlib import Path
from types import ModuleType
from typing import Union

from sanic.blueprints import Blueprint


def autodiscover(
    app, *module_names: Union[str, ModuleType], recursive: bool = False
):
    mod = app.__module__
    blueprints = set()
    _imported = set()

    def _find_bps(module):
        nonlocal blueprints

        for _, member in getmembers(module):
            if isinstance(member, Blueprint):
                blueprints.add(member)

    for module in module_names:
        if isinstance(module, str):
            module = import_module(module, mod)
            _imported.add(module.__file__)
        _find_bps(module)

        if recursive:
            base = Path(module.__file__).parent
            for path in glob(f"{base}/**/*.py", recursive=True):
                if path not in _imported:
                    name = "module"
                    if "__init__" in path:
                        *_, name, __ = path.split("/")
                    spec = util.spec_from_file_location(name, path)
                    specmod = util.module_from_spec(spec)
                    _imported.add(path)
                    spec.loader.exec_module(specmod)
                    _find_bps(specmod)

    for bp in blueprints:
        app.blueprint(bp)


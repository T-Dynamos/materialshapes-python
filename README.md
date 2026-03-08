# materialshapes-python
<p align="center">
  <img src="https://firebasestorage.googleapis.com/v0/b/design-spec/o/projects%2Fgoogle-material-3%2Fimages%2Fm0c35amt-1.png?alt=media&token=ab563092-217d-4d71-986d-1b4d87b5ba3e" width="50%">
</p>

A complete Python port of the official Material Design 3 shape system from Android. It includes rounded polygon generation, shape morphing, and smooth transitions based on Google's original Java source.

Uses both ThorVG and PyCairo for 2D graphics rendering. Both backends return RGBA bytes of shapes. In ThorVG, it uses a centralized engine with multi-threading to maximize performance. A Kivy widget is already included.

## Rendering Backends

The `materialshapes.renderer` module supports two backends:
- **ThorVG**: Uses `thorvg-python` bindings.
- **PyCairo**: Uses `pycairo` for rendering.

Both backends are accessible through the `render` function.

[Material Design Shape System](https://m3.material.io/styles/shape/overview-principles)


## Docs

There is no separate documentation yet.

The examples serve as the documentation and cover all major features.
Check them out to understand usage and integration.

## Install

You can install the core library, but you **must** install at least one rendering backend:

```console
# To use ThorVG (Recommended for performance)
pip3 install "materialshapes[thorvg]"

# To use Cairo
pip3 install "materialshapes[cairo]"

# To install both
pip3 install "materialshapes[all]"
```

## Examples


File: `kivy.py`

Run using:
```
python3 -m examples.kivy
```

https://github.com/user-attachments/assets/31c2ae03-9be8-4a34-b95d-b7e7219773b1


File: `loading_indicator.py`

Run using:
```
python3 -m examples.loading_indicator
```


https://github.com/user-attachments/assets/c52553f1-c4f0-4af1-8360-f72acfd78949

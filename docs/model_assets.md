# Model Assets

The repository does not include large model files such as `.onnx` or `.pt`.
These files should be downloaded separately from the project cloud drive and
placed in the paths below.

## Required for GUI Runtime

The blink-call GUI loads the ONNX eye-state classifier through
`blink_call/algorithm/eye_state_classifier.py`.

Download:

| File | Required | Target path |
| --- | --- | --- |
| `eye3_mixed_unknown_convnext_tiny_128_fp32.onnx` | Yes | `ViTA/exports/eye3_mixed_unknown_convnext_tiny_128_fp32.onnx` |

Cloud drive link:

```text
Baidu Netdisk: https://pan.baidu.com/s/1ckwmel8RH9ATeNmxaRACng?pwd=5842
Extraction code: 5842
```

Expected directory layout after download:

```text
blink-call/
`-- ViTA/
    `-- exports/
        |-- eye3_mixed_unknown_convnext_tiny_128_fp32.json
        `-- eye3_mixed_unknown_convnext_tiny_128_fp32.onnx
```

The `.json` metadata file is tracked by Git. The `.onnx` model file must be
downloaded manually.

## Optional Training Checkpoints

The `.pt` checkpoint files are only needed when reproducing training,
evaluation, or benchmarking workflows under `ViTA/vita/`. They are not required
to launch the GUI.

Download if needed:

| File | Required | Target path |
| --- | --- | --- |
| `best.pt` | No | `ViTA/ckp/eye3_mixed_unknown_convnext_tiny_128_finetune/best.pt` |
| `last.pt` | No | `ViTA/ckp/eye3_mixed_unknown_convnext_tiny_128_finetune/last.pt` |

Cloud drive link:

```text
Baidu Netdisk: https://pan.baidu.com/s/19njfqm5ix-VBWmMoNCPSMA?pwd=5842
Extraction code: 5842
```

## Verification

After downloading the runtime ONNX file, run:

```bash
ls -lh ViTA/exports/eye3_mixed_unknown_convnext_tiny_128_fp32.onnx
```

If the ONNX file is missing, the GUI can still start, but the classifier will
return `unknown` states and report a model loading error in debug output.

import onnxruntime as ort


def available_providers(ctx_id: int):
    available = ort.get_available_providers()
    if ctx_id >= 0 and "CUDAExecutionProvider" in available:
        return [
            ("CUDAExecutionProvider", {"device_id": ctx_id}),
            "CPUExecutionProvider",
        ]
    return ["CPUExecutionProvider"]


def create_ort_session(onnx_path, ctx_id=0):
    options = ort.SessionOptions()
    options.intra_op_num_threads = 1
    options.inter_op_num_threads = 1
    options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

    return ort.InferenceSession(
        str(onnx_path),
        sess_options=options,
        providers=available_providers(ctx_id),
    )

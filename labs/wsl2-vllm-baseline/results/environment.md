## 환경
측정일 2026-08-15 01:35 UTC
name, memory.total [MiB], driver_version
NVIDIA GeForce RTX 4080 Laptop GPU, 12282 MiB, 581.57
power.limit:
[N/A]
6.18.33.1-microsoft-standard-WSL2
Python 3.14.4
vllm/vllm-openai:v0.23.0
MODEL_ID=Qwen/Qwen2.5-1.5B-Instruct
SERVED_MODEL_NAME=qwen2.5-1.5b
MAX_NUM_SEQS=16
MAX_MODEL_LEN=4096
GPU_MEMORY_UTILIZATION=0.85
{
    "object": "list",
    "data": [
        {
            "id": "qwen2.5-1.5b",
            "object": "model",
            "created": 1786757714,
            "owned_by": "vllm",
            "root": "Qwen/Qwen2.5-1.5B-Instruct",
            "parent": null,
            "max_model_len": 4096,
            "permission": [
                {
                    "id": "modelperm-b8272977e5dd16c1",
                    "object": "model_permission",
                    "created": 1786757714,
                    "allow_create_engine": false,
                    "allow_sampling": true,
                    "allow_logprobs": true,
                    "allow_search_indices": false,
                    "allow_view": true,
                    "allow_fine_tuning": false,
                    "organization": "*",
                    "group": null,
                    "is_blocking": false
                }
            ]
        }
    ]
}

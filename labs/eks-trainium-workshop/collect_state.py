"""워크샵 root 셸에서 실행하는 읽기 전용 상태 수집기. Secret은 읽지 않는다."""
import datetime
import json
import subprocess


def run(*args):
    return subprocess.check_output(args, text=True, timeout=45).strip()


def kubectl(*args):
    return json.loads(run("kubectl", *args, "-o", "json", "--request-timeout=30s"))


def pod_state(pod):
    return {
        "name": pod["metadata"]["name"],
        "namespace": pod["metadata"]["namespace"],
        "node": pod["spec"].get("nodeName"),
        "status": pod["status"],
    }


def main():
    deployment = kubectl("get", "deployment", "vllm-deployment")
    config = kubectl("get", "configmap", "vllm-shared-config")["data"]
    ingress = kubectl("get", "ingress", "vllm-ingress-simple")
    safe_keys = (
        "MODEL_NAME", "MAX_NUM_SEQS", "MAX_MODEL_LEN", "TENSOR_PARALLEL_SIZE", "PORT",
        "NEURON_COMPILED_ARTIFACTS", "NEURON_COMPILE_CACHE_URL", "VLLM_NEURON_FRAMEWORK",
    )
    result = {
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "context": run("kubectl", "config", "current-context"),
        "nodes": [
            {"name": node["metadata"]["name"],
             "instance_type": node["metadata"]["labels"].get("node.kubernetes.io/instance-type"),
             "kubelet_version": node["status"]["nodeInfo"]["kubeletVersion"],
             "allocatable": node["status"]["allocatable"],
             "taints": node["spec"].get("taints", [])}
            for node in kubectl("get", "nodes")["items"]
        ],
        "vllm_deployment": {
            "strategy": deployment["spec"]["strategy"], "status": deployment["status"],
            "image": deployment["spec"]["template"]["spec"]["containers"][0]["image"],
            "readiness_probe": deployment["spec"]["template"]["spec"]["containers"][0].get("readinessProbe"),
        },
        "vllm_pods": [pod_state(p) for p in kubectl("get", "pods", "-l", "app.kubernetes.io/name=vllm-server")["items"]],
        "controller_pods": [pod_state(p) for p in kubectl("get", "pods", "-n", "ingress-nginx", "-l", "app.kubernetes.io/component=controller")["items"]],
        "config": {key: config.get(key) for key in safe_keys},
        "ingress": {"spec": ingress["spec"], "status": ingress["status"]},
        "helm": json.loads(run("helm", "list", "-n", "ingress-nginx", "-o", "json")),
        "services": [],
        "pending_events": [],
    }
    for namespace, name in (("default", "vllm-service"), ("ingress-nginx", "ingress-nginx-controller")):
        service = kubectl("get", "service", name, "-n", namespace)
        result["services"].append({"namespace": namespace, "name": name, "spec": service["spec"], "status": service["status"]})
    for event in kubectl("get", "events", "--field-selector", "reason=FailedScheduling")["items"]:
        if event["involvedObject"]["name"].startswith("vllm-deployment-"):
            result["pending_events"].append({key: event.get(key) for key in ("involvedObject", "message", "lastTimestamp", "count")})
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

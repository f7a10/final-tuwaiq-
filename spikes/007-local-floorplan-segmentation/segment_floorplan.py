from local_floorplan import parse_args, run


if __name__ == "__main__":
    result = run(parse_args())
    performance = result["performance"]
    print(
        f"rooms={len(result['rooms'])} "
        f"load={performance['model_load_seconds']}s "
        f"inference={performance['inference_seconds']}s "
        f"peak_rss={performance['peak_rss_mb']}MB"
    )

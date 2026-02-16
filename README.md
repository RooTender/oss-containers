# OSS Containers

A small collection of containerized open-source applications prepared for simple self-hosted deployment.  
Images are built automatically from upstream sources and published to GitHub Container Registry.

## Philosophy

This repository acts as a distribution layer, not a fork of the upstream projects.  
Upstream code remains unchanged while builds focus on reproducibility and operational usability.  
Containers are prepared with sane defaults for operators who just want to run the software.

## Available Containers

| Name | Description |
|------|-------------|
| [Parabol](https://github.com/ParabolInc/parabol) | Open-source agile meeting and retrospective platform |

## Example

```bash
docker run -d \
  --name parabol \
  -p 3000:3000 \
  --env-file .env \
  ghcr.io/rootender/oss-containers/parabol:latest
```

This and other `docker-compose` examples you can find in the [examples](examples/) folder.

## License

Each container follows the license of its upstream project. See individual repositories for details.

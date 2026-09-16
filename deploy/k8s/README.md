# Kubernetes 部署

## 部署顺序

```bash
# 1. 创建命名空间
kubectl create namespace supply-chain

# 2. 创建 Secret（先复制模板并填入真实值）
cp secrets.example.yaml secrets.yaml
vim secrets.yaml
kubectl apply -f secrets.yaml

# 3. 创建 ConfigMap
kubectl apply -f configmap.yaml

# 4. 部署基础设施（MySQL → Redis → RabbitMQ）
kubectl apply -f mysql.yaml
kubectl apply -f redis.yaml
kubectl apply -f rabbitmq.yaml

# 5. 等待基础设施就绪
kubectl -n supply-chain rollout status statefulset/mysql
kubectl -n supply-chain rollout status deployment/redis
kubectl -n supply-chain rollout status statefulset/rabbitmq

# 6. 部署应用
kubectl apply -f app.yaml
kubectl apply -f hpa.yaml

# 7. 部署 Ingress（需已安装 nginx-ingress 并创建 app-tls 证书）
kubectl apply -f ingress.yaml
```

## 数据库迁移

多副本并发运行 Alembic 迁移有风险。迁移变更时用 Job 单独执行：

```bash
kubectl -n supply-chain run alembic-migrate \
  --image=supply-chain-risk-control:latest \
  --restart=Never \
  --env-from=configmap/app-config --env-from=secret/app-secrets \
  --command -- alembic upgrade head
```

## 注意事项

- `app-config.yaml` 中的 `DATABASE_URL` 使用了 `$(MYSQL_ROOT_PASSWORD)` env 引用语法，
  实际部署时建议改为在 Deployment 中用 `secretKeyRef` 拼接，或改用 External Secrets
- MySQL/RabbitMQ 为单实例 StatefulSet，生产高可用建议使用云托管服务
- 镜像默认从本地加载（`imagePullPolicy: IfNotPresent`），需先推送到镜像仓库并修改 `app.yaml` 中的镜像地址
- Prometheus 抓取 `/metrics` 端点：为 app Pod 添加
  `prometheus.io/scrape: "true"` / `prometheus.io/port: "8000"` 注解即可

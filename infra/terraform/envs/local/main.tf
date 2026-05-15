module "cluster_config" {
  source = "../../modules/k8s-cluster"

  cluster_name       = var.cluster_name
  node_count         = var.node_count
  gpu_node_count     = 0  # kind does not expose GPU devices
  kubernetes_version = var.kubernetes_version
}

# ─── kind cluster ────────────────────────────────────────────────────────────

resource "kind_cluster" "this" {
  name           = module.cluster_config.cluster_name
  node_image     = "kindest/node:v${module.cluster_config.kubernetes_version}"
  wait_for_ready = true

  kind_config {
    kind        = "Cluster"
    api_version = "kind.x-k8s.io/v1alpha4"

    node {
      role = "control-plane"
    }

    dynamic "node" {
      for_each = range(module.cluster_config.node_count)
      content {
        role = "worker"
      }
    }
  }
}

# ─── Helm provider (wired to the kind cluster) ───────────────────────────────

provider "helm" {
  kubernetes {
    host                   = kind_cluster.this.endpoint
    client_certificate     = kind_cluster.this.client_certificate
    client_key             = kind_cluster.this.client_key
    cluster_ca_certificate = kind_cluster.this.cluster_ca_certificate
  }
}

provider "kubernetes" {
  host                   = kind_cluster.this.endpoint
  client_certificate     = kind_cluster.this.client_certificate
  client_key             = kind_cluster.this.client_key
  cluster_ca_certificate = kind_cluster.this.cluster_ca_certificate
}

# ─── MetalLB — LoadBalancer simulation ───────────────────────────────────────
# ref: https://metallb.universe.tf/installation/

resource "helm_release" "metallb" {
  name             = "metallb"
  repository       = "https://metallb.github.io/metallb"
  chart            = "metallb"
  version          = var.metallb_chart_version
  namespace        = "metallb-system"
  create_namespace = true
  wait             = true
  timeout          = 300

  depends_on = [kind_cluster.this]
}

# MetalLB CRDs are created by the Helm chart; wait for the webhook to be ready
# before applying IPAddressPool / L2Advertisement manifests.
resource "kubernetes_manifest" "metallb_ip_pool" {
  depends_on = [helm_release.metallb]

  manifest = {
    apiVersion = "metallb.io/v1beta1"
    kind       = "IPAddressPool"
    metadata = {
      name      = "local-pool"
      namespace = "metallb-system"
    }
    spec = {
      addresses = [var.metallb_address_pool]
    }
  }
}

resource "kubernetes_manifest" "metallb_l2_advertisement" {
  depends_on = [kubernetes_manifest.metallb_ip_pool]

  manifest = {
    apiVersion = "metallb.io/v1beta1"
    kind       = "L2Advertisement"
    metadata = {
      name      = "local-advert"
      namespace = "metallb-system"
    }
    spec = {
      ipAddressPools = ["local-pool"]
    }
  }
}

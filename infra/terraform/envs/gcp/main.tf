module "cluster_config" {
  source = "../../modules/k8s-cluster"

  cluster_name         = var.cluster_name
  node_count           = var.node_count
  gpu_node_count       = var.gpu_node_count
  gpu_instance_type    = "n1-standard-4"  # GCP machine type for GPU nodes
  kubernetes_version   = var.kubernetes_version
}

locals {
  network_name    = "${module.cluster_config.cluster_name}-vpc"
  subnetwork_name = "${module.cluster_config.cluster_name}-subnet"

  # GPU node pool definition — conditionally appended to node_pools list.
  gpu_pool = var.gpu_node_count > 0 ? [
    {
      name               = "gpu-pool"
      machine_type       = "n1-standard-4"
      min_count          = 0
      max_count          = module.cluster_config.gpu_node_count
      initial_node_count = 0
      auto_repair        = true
      auto_upgrade       = true
      image_type         = "COS_CONTAINERD"
      disk_size_gb       = 100
      disk_type          = "pd-ssd"
      accelerator_count  = 1
      accelerator_type   = var.gpu_accelerator_type
      gpu_driver_version = "LATEST"
    }
  ] : []

  node_pools = concat(
    [
      {
        name               = "cpu-pool"
        machine_type       = "n2-standard-4"
        min_count          = 1
        max_count          = module.cluster_config.node_count + 2
        initial_node_count = module.cluster_config.node_count
        auto_repair        = true
        auto_upgrade       = true
        image_type         = "COS_CONTAINERD"
        disk_size_gb       = 100
        disk_type          = "pd-ssd"
      }
    ],
    local.gpu_pool,
  )

  # Taints for GPU nodes — NO_SCHEDULE so only GPU-aware workloads land there.
  node_pools_taints = merge(
    {
      all      = []
      cpu-pool = []
    },
    var.gpu_node_count > 0 ? {
      gpu-pool = [
        {
          key    = "nvidia.com/gpu"
          value  = "present"
          effect = "NO_SCHEDULE"
        }
      ]
    } : {},
  )
}

# ─── VPC ─────────────────────────────────────────────────────────────────────

resource "google_compute_network" "vpc" {
  name                    = local.network_name
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "subnet" {
  name          = local.subnetwork_name
  network       = google_compute_network.vpc.self_link
  region        = var.region
  ip_cidr_range = "10.0.0.0/20"

  secondary_ip_range {
    range_name    = "${module.cluster_config.cluster_name}-pods"
    ip_cidr_range = "10.1.0.0/16"
  }

  secondary_ip_range {
    range_name    = "${module.cluster_config.cluster_name}-services"
    ip_cidr_range = "10.2.0.0/20"
  }
}

# ─── GKE ─────────────────────────────────────────────────────────────────────
# ref: https://registry.terraform.io/modules/terraform-google-modules/kubernetes-engine/google/44.1.0

module "gke" {
  source  = "terraform-google-modules/kubernetes-engine/google"
  version = "~> 44.1"

  project_id         = var.project_id
  name               = module.cluster_config.cluster_name
  region             = var.region
  zones              = var.zones
  network            = google_compute_network.vpc.name
  subnetwork         = google_compute_subnetwork.subnet.name
  ip_range_pods      = "${module.cluster_config.cluster_name}-pods"
  ip_range_services  = "${module.cluster_config.cluster_name}-services"
  kubernetes_version = module.cluster_config.kubernetes_version
  deletion_protection = var.deletion_protection

  release_channel = "REGULAR"

  # Workload Identity — automatically sets [project_id].svc.id.goog pool.
  identity_namespace = "enabled"

  # Required for Workload Identity to work on each node.
  # ref: https://cloud.google.com/kubernetes-engine/docs/how-to/workload-identity
  node_metadata = "GKE_METADATA"

  http_load_balancing        = true
  horizontal_pod_autoscaling = true

  node_pools            = local.node_pools
  node_pools_taints     = local.node_pools_taints
  node_pools_labels     = { all = {}, cpu-pool = {} }
  node_pools_tags       = { all = [], cpu-pool = [] }
  node_pools_oauth_scopes = {
    all = ["https://www.googleapis.com/auth/cloud-platform"]
  }

  depends_on = [
    google_compute_subnetwork.subnet,
  ]
}

# ─── Artifact Registry ────────────────────────────────────────────────────────

resource "google_artifact_registry_repository" "audiomind" {
  location      = var.region
  repository_id = "audiomind"
  format        = "DOCKER"
  description   = "AudioMind MLOps container images"
}

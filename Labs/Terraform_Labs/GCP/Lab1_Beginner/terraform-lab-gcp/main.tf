provider "google" {
  project = "terraform-lab-514821"
  region  = "us-central1"
  zone    = "us-central1-a"
}

resource "google_compute_instance" "vm_instance" {
  name                      = "terraform-vm"
  machine_type              = "e2-micro"
  zone                      = "us-central1-a"
  allow_stopping_for_update = true


  labels = {
    environment = "development"
    owner       = "team-terraform"
  }

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-12"
      size  = 12
    }
  }

  network_interface {
    network = "default"
  }
}

resource "google_storage_bucket" "terraform-lab-bucket" {
  name                        = "terraform-lab-bucket-1"
  location                    = "us-central1"
  force_destroy               = true
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
}

resource "google_storage_bucket_object" "readme" {
  name    = "hello.txt"
  bucket  = google_storage_bucket.terraform-lab-bucket.name
  content = "Created by Terraform on ${google_compute_instance.vm_instance.name}"
}
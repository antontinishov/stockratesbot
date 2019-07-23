provider "azurerm" { }

data "azurerm_resource_group" "prod" {
  name = "${var.resource_group}"
}

data "azurerm_virtual_network" "prod" {
  name                = "${var.resource_group}-vnet"
  resource_group_name = "${data.azurerm_resource_group.prod.name}"
}

data "azurerm_subnet" "prod" {
  name                 = "default"
  resource_group_name  = "${data.azurerm_resource_group.prod.name}"
  virtual_network_name = "${data.azurerm_virtual_network.prod.name}"
}

resource "azurerm_public_ip" "prod" {
  name                = "${var.nodename}IP"
  location            = "${data.azurerm_resource_group.prod.location}"
  resource_group_name = "${data.azurerm_resource_group.prod.name}"
  public_ip_address_allocation = "static"
}

data "azurerm_network_security_group" "prod" {
  name                = "master-nsg"
  resource_group_name = "${data.azurerm_resource_group.prod.name}"
}

resource "azurerm_network_interface" "prod" {
  name                = "${var.nodename}"
  location            = "${data.azurerm_resource_group.prod.location}"
  resource_group_name = "${data.azurerm_resource_group.prod.name}"
  network_security_group_id = "${data.azurerm_network_security_group.prod.id}"

  ip_configuration {
    name                          = "${var.nodename}ip"
    subnet_id                     = "${data.azurerm_subnet.prod.id}"
    private_ip_address_allocation = "static"
    private_ip_address            = "10.0.0.21"
    public_ip_address_id          = "${azurerm_public_ip.prod.id}"
  }
}


data "azurerm_storage_account" "prod" {
  name                 = "${var.resource_group}diag249"
  resource_group_name  = "${data.azurerm_resource_group.prod.name}"
}

resource "azurerm_virtual_machine" "node-vm" {
  name                  = "${var.nodename}"
  location              = "${data.azurerm_resource_group.prod.location}"
  resource_group_name   = "${data.azurerm_resource_group.prod.name}"
  network_interface_ids = ["${azurerm_network_interface.prod.id}"]
  vm_size               = "Standard_F2s_v2"
  delete_os_disk_on_termination = true

  boot_diagnostics {
    enabled       = "true"
    storage_uri   = "${data.azurerm_storage_account.prod.primary_blob_endpoint}"
  }

  storage_image_reference {
    publisher = "Canonical"
    offer     = "UbuntuServer"
    sku       = "16.04-LTS"
    version   = "latest"
  }

  storage_os_disk {
    name              = "${var.nodename}_OsDisk"
    caching           = "ReadWrite"
    create_option     = "FromImage"
    managed_disk_type = "Premium_LRS"
    disk_size_gb      = "50"
  }

  os_profile {
    computer_name  = "${var.nodename}"
    admin_username = "${var.admin_username}"
    admin_password = "${var.admin_password}"
  }

  os_profile_linux_config {
    disable_password_authentication = true
    ssh_keys = [{
      path = "/home/anton/.ssh/authorized_keys"
      key_data = "${file("~/.ssh/id_rsa.pub")}"
    }]
  }
  provisioner "local-exec" {
    command = "sleep 30 && printf \"[nodes]\n${data.azurerm_public_ip.prod.ip_address}\" > /docker/stockratesbot/deploy/ansible/inventory && python3 /usr/local/bin/ansible-playbook -i /docker/stockratesbot/deploy/ansible/inventory /docker/stockratesbot/deploy/ansible/run.yml"
  }

  tags {
    environment = "prod"
  }
}

  data "azurerm_public_ip" "prod" {
    name                = "${azurerm_public_ip.prod.name}"
    resource_group_name = "${data.azurerm_resource_group.prod.name}"
  }

  output "public_ip_address" {
    value = "${data.azurerm_public_ip.prod.ip_address}"
  }
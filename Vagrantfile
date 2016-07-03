# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure(2) do |config|

    # NOTE: Ordering matters! The commissaire box should be the
    #       the last box to start!

    # Development etcd server.
    config.vm.define "etcd" do |etcd|
      etcd.vm.box = "fedora/24-cloud-base"
      etcd.vm.network "private_network", ip: "192.168.152.101"
      etcd.vm.provision "shell", inline: <<-SHELL
        echo "==> Setting hostname"
        sudo hostnamectl set-hostname etcd
        #echo "===> Updating the system"
        sudo dnf update --setopt=tsflags=nodocs -y
        echo "===> Installing etcd"
        sudo dnf install -y etcd
        echo "===> Configuring etcd"
        sudo sed -i "s/localhost/192.168.152.101/g" /etc/etcd/etcd.conf
        echo "===> Starting etcd"
        sudo systemctl enable etcd
        sudo systemctl start etcd
      SHELL
    # End etcd
    end

    # Development Node 1
    config.vm.define "fedora-cloud" do |node|
      node.vm.box = "fedora/24-cloud-base"
      node.vm.network "private_network", ip: "192.168.152.110"
      node.vm.provision "shell", inline: <<-SHELL
        echo "==> Setting hostname"
        sudo hostnamectl set-hostname fedora-cloud
        echo "===> Updating the system"
        sudo dnf update --setopt=tsflags=nodocs -y
      SHELL
    # End etcd
    end

    # Development Node 1
    config.vm.define "fedora-atomic" do |node|
      node.vm.box = "fedora/23-atomic-host"
      node.vm.network "private_network", ip: "192.168.152.111"
      node.vm.provision "shell", inline: <<-SHELL
        echo "==> Setting hostname"
        sudo hostnamectl set-hostname fedora-atomic
        echo "===> Updating the system"
        sudo atomic host upgrade
        sudo systemctl reboot
      SHELL
    # End node2
    end

  # Development commissaire server
  config.vm.define "commissaire", primary: true do |commissaire|
    commissaire.vm.box = "fedora/24-cloud-base"
    commissaire.vm.network "private_network", ip: "192.168.152.100"
    commissaire.vm.provision "shell", inline: <<-SHELL
      echo "==> Setting hostname"
      sudo hostnamectl set-hostname commissaire
      echo "===> Updating the system"
      sudo dnf update -y
      echo "===> Installing OS dependencies"
      sudo dnf install -y --setopt=tsflags=nodocs rsync openssh-clients redhat-rpm-config python-virtualenv gcc libffi-devel openssl-devel
      echo "===> Setting up virtualenv"
      virtualenv commissaire_env
      . commissaire_env/bin/activate && pip install -U -r /vagrant/test-requirements.txt
      . commissaire_env/bin/activate && pip install -e /vagrant/
      echo "===> Setting up commissaire to autostart"
      sudo cp /vagrant/contrib/systemd/commissaire.service /etc/systemd/system/commissaire.service
      sudo chmod 644 /etc/systemd/system/commissaire.service
      sudo mkdir /etc/commissaire
      sudo cp /vagrant/conf/commissaire.conf /etc/commissaire/commissaire.conf
      sudo sed -i 's|127.0.0.1|192.168.152.100|g' /etc/commissaire/commissaire.conf
      sudo sed -i 's|^ExecStart=.*|ExecStart=/bin/bash -c ". /home/vagrant/commissaire_env/bin/activate \\&\\& commissaire -c /etc/commissaire/commissaire.conf"|' /etc/systemd/system/commissaire.service
      sudo sed -i 's|Type=simple|\&\\nWorkingDirectory=/vagrant|' /etc/systemd/system/commissaire.service
      sudo systemctl daemon-reload
      echo "===> Starting commissaire"
      sudo systemctl enable commissaire
      sudo systemctl start commissaire
    SHELL
  # End commissaire
  end

# End config
end

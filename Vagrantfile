# -*- mode: ruby -*-
# vi: set ft=ruby :

# Vagrantfile API/syntax version. Don't touch unless you know what you're doing!
VAGRANTFILE_API_VERSION = "2"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|

	# VAGRANT BASE BOX
	config.vm.box = "centos-6.5-x86_64-vagrant"
	config.vm.box_url = "https://db.tt/WJ2WsxVq"

	# FORWARDED PORT MAPPING
	config.vm.network :forwarded_port, guest: 80, host: 80

	# SET UP STATIC PRIVATE IP
	config.vm.network :private_network, ip: "192.168.111.222"

	# VIRTUALBOX SPECIFIC CONFIGURATION
	config.vm.provider :virtualbox do |vb|

		# BOOT INTO A GUI
		vb.gui = true

		# CHANGE THE NAME
		vb.name = "OpenPolarServer"

		# CHANGE THE HARDWARE ALLOTMENT
		vb.customize ["modifyvm", :id, "--memory", "1536"]
		vb.customize ["modifyvm", :id, "--cpus", "2"]

	end

	# ENABLE SHELL PROVISIONING
	config.vm.provision :shell, :path => "conf/provisions.sh"

end

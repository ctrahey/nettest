RESOURCE_GROUP=TraheyNetTest
LB_NAME=TraheyNetTestLB

az group create --name TraheyNetTest --location westus

az network vnet create \
   --resource-group $RESOURCE_GROUP \
   --location westus \
   --name NetTest \
   --address-prefixes 10.1.0.0/16 \
   --subnet-name NetTestBackendSubnet \
   --subnet-prefixes 10.1.0.0/24

az network public-ip create \
  --resource-group $RESOURCE_GROUP \
  --name TraheyNetTest \
  --sku Standard

az network lb create \
  --resource-group $RESOURCE_GROUP \
  --name $LB_NAME \
  --sku Standard \
  --public-ip-address TraheyNetTest \
  --frontend-ip-name TraheyNetTestFrontEnd \
  --backend-pool-name TraheyNetTestBackend

az network lb probe create \
  --resource-group $RESOURCE_GROUP \
  --lb-name $LB_NAME \
  --name myHealthProbe \
  --protocol tcp \
  --port 80

az network lb rule create \
  --resource-group $RESOURCE_GROUP \
  --lb-name $LB_NAME \
  --name myHTTPRule \
  --protocol tcp \
  --frontend-port 80 \
  --backend-port 80 \
  --frontend-ip-name TraheyNetTestFrontEnd \
  --backend-pool-name TraheyNetTestBackend \
  --probe-name myHealthProbe \
  --disable-outbound-snat true \
  --idle-timeout 15 \
  --enable-tcp-reset true

az network nsg create \
  --resource-group $RESOURCE_GROUP \
  --name TraheyNettestNSG

az network nsg rule create \
  --resource-group $RESOURCE_GROUP \
  --nsg-name TraheyNettestNSG \
  --name myNSGRuleHTTP \
  --protocol '*' \
  --priority 204
LB_NAME=TraheyNetTestLB
az group create --name TraheyNetTest --location westus

az network vnet create \
   --resource-group $RESOURCE_GROUP \
   --location westus \
   --name NetTest \
   --address-prefixes 10.1.0.0/16 \
   --subnet-name NetTestBackendSubnet \
   --subnet-prefixes 10.1.0.0/24

az network public-ip create \
  --resource-group $RESOURCE_GROUP \
  --name TraheyNetTest \
  --sku Standard

az network lb create \
  --resource-group $RESOURCE_GROUP \
  --name $LB_NAME \
  --sku Standard \
  --public-ip-address TraheyNetTest \
  --frontend-ip-name TraheyNetTestFrontEnd \
  --backend-pool-name TraheyNetTestBackend

az network lb probe create \
  --resource-group $RESOURCE_GROUP \
  --lb-name $LB_NAME \
  --name myHealthProbe \
  --protocol tcp \
  --port 80

az network lb rule create \
  --resource-group $RESOURCE_GROUP \
  --lb-name $LB_NAME \
  --name myHTTPRule \
  --protocol tcp \
  --frontend-port 80 \
  --backend-port 80 \
  --frontend-ip-name TraheyNetTestFrontEnd \
  --backend-pool-name TraheyNetTestBackend \
  --probe-name myHealthProbe \
  --disable-outbound-snat true \
  --idle-timeout 15 \
  --enable-tcp-reset true

az network nsg create \
  --resource-group $RESOURCE_GROUP \
  --name TraheyNettestNSG

az network nsg rule create \
  --resource-group $RESOURCE_GROUP \
  --nsg-name TraheyNettestNSG \
  --name myNSGRuleHTTP \
  --protocol '*' \
  --direction inbound \
  --source-address-prefix '*' \
  --source-port-range '*' \
  --destination-address-prefix '*' \
  --destination-port-range 80 \
  --access allow \
  --priority 200

az network vnet subnet create \
  --resource-group $RESOURCE_GROUP \
  --name AzureBastionSubnet \
  --vnet-name NetTest \
  --address-prefixes 10.1.1.0/27

az network public-ip create \
  --resource-group $RESOURCE_GROUP \
  --name TraheyNettestBastionIP \
  --sku Standard

az network bastion create \
  --resource-group $RESOURCE_GROUP \
  --name TraheyBastionHost \
  --public-ip-address TraheyNettestBastionIP \
  --vnet-name NetTest \
  --location westus

array=(myNicVM1)
for vmnic in "${array[@]}"
do
  az network nic create \
      --resource-group $RESOURCE_GROUP \
      --name $vmnic \
      --vnet-name NetTest \
      --subnet NetTestBackendSubnet \
      --network-security-group TraheyNettestNSG
done

az vm create --resource-group $RESOURCE_GROUP \
  --name myVM1 \
  --nics myNicVM1 \
  --image Canonical:0001-com-ubuntu-server-jammy:22_04-lts-gen2:latest \
  --admin-username unsructured \
  --user-data ./start-service-init.sh \
  --size Standard_D8s_v5 \
  --ssh-key-values ~/.ssh/id_ed25519.pub

array=("myNicVM1")
for vmnic in "${array[@]}"
do
  az network nic ip-config address-pool add \
   --address-pool TraheyNetTestBackend \
   --ip-config-name ipconfig1 \
   --nic-name $vmnic \
   --resource-group $RESOURCE_GROUP \
   --lb-name $LB_NAME
done


az network public-ip create \
  --resource-group $RESOURCE_GROUP \
  --name TraheyNettestNATgatewayIP \
  --sku Standard

az network nat gateway create \
  --resource-group $RESOURCE_GROUP \
  --name TraheyNettestNATgateway \
  --public-ip-addresses TraheyNettestNATgatewayIP \
  --idle-timeout 10

az network vnet subnet update --resource-group $RESOURCE_GROUP --vnet-name NetTest --name NetTestBackendSubnet --nat-gateway TraheyNettestNATgateway

az network public-ip show --resource-group $RESOURCE_GROUP --name TraheyNetTest --query ipAddress --output tsv

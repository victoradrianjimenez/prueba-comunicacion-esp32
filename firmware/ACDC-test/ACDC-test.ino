#define SUPERVISOR  // comentar esta línea para grabar el NodoTest

#ifdef SUPERVISOR
String NombreNodo = "Supervisor";
#endif
#ifndef SUPERVISOR
String NombreNodo = "NodoTest001";
#endif

#include "namedMesh.h"
#include "cred.h"
#include <ArduinoJson.h>

#define	PeriodoEnvioDatos 1000 //tiempo en milisegundos
String supervisorName = "Supervisor";

void sendKeepAlive(); 
void receivedCallback(uint32_t from, String & msg);
void newConnectionCallback(uint32_t nodeId);
void changedConnectionCallback(); 

Scheduler  userScheduler;
namedMesh  mesh;
SimpleList<uint32_t> nodes;
SimpleList<uint32_t>::iterator node;
Task taskSendKeepAlive( PeriodoEnvioDatos, TASK_FOREVER, &sendKeepAlive );


void setup() {
  Serial.begin(115200);
  delay(1000);
  //mesh.setDebugMsgTypes( ERROR | MESH_STATUS | CONNECTION | SYNC | COMMUNICATION | GENERAL | MSG_TYPES | REMOTE ); // all types on  
  mesh.setDebugMsgTypes(ERROR | DEBUG | MESH_STATUS);
  mesh.init(MESH_SSID, MESH_PASSWORD, &userScheduler, MESH_PORT,WIFI_AP_STA);
  //mesh.init(MESH_SSID, MESH_PASSWORD, &userScheduler, MESH_PORT,WIFI_AP_STA,1,1); //para iniciar la red wifi oculta
  mesh.setName(NombreNodo);
  mesh.onReceive(&receivedCallback);
  mesh.onNewConnection(&newConnectionCallback);
  mesh.onChangedConnections(&changedConnectionCallback);

#ifndef SUPERVISOR
  userScheduler.addTask( taskSendKeepAlive );
  taskSendKeepAlive.enable();
#endif
}

DynamicJsonDocument DatosSerial(1024);

void loop() {
  mesh.update();
  if (Serial.available()>0){
    // leer mensaje desde el puerto serie
    String msg=Serial.readStringUntil('\n');
    // parsear mensaje
    deserializeJson(DatosSerial, msg);
    const char* DestinoMensaje=DatosSerial["destiny"];
    String destinoMensaje = String (DestinoMensaje);
    // enviar mensaje al destinatario
    String DatosJSON;  
    serializeJson(DatosSerial,DatosJSON);
    Serial.println(DatosJSON);
    mesh.sendSingle(destinoMensaje, DatosJSON);
  }
}

void sendKeepAlive(){
  DynamicJsonDocument DatosSerie(1024);
  DatosSerie.clear();
  DatosSerie["origin"]=NombreNodo;
  DatosSerie["timestamp"]=millis(); 
  DatosSerie["class"]="keepAlive";

  String DatosJSON;
  serializeJson(DatosSerie, DatosJSON);
  Serial.println(DatosJSON);
#ifndef SUPERVISOR
  mesh.sendSingle(supervisorName, DatosJSON);
#endif
}

void receivedCallback(uint32_t from, String & msg) {
  DynamicJsonDocument DatosSerie(1024);
  deserializeJson(DatosSerie, msg);
  const char* OrigenMensaje=DatosSerie["origin"];

  String DatosJSON;
  serializeJson(DatosSerie,DatosJSON);
  Serial.println(DatosJSON);

#ifndef SUPERVISOR
  if (String (OrigenMensaje)=="Supervisor"){
    DynamicJsonDocument Response(1024);
    Response.clear();
    Response["origin"]=NombreNodo;
    Response["timestamp"]=millis(); 
    Response["class"]="received";
    Response["origin_ts"]=DatosSerie["timestamp"];

    String DatosJSON;
    serializeJson(Response, DatosJSON);
    Serial.println(DatosJSON);
    mesh.sendSingle(supervisorName, DatosJSON);
  }
#endif
}

void newConnectionCallback(uint32_t nodeId) {
  DynamicJsonDocument DatosSerie(1024);
  DatosSerie.clear();
  DatosSerie["origin"]=NombreNodo;
  DatosSerie["timestamp"]=millis(); 
  DatosSerie["class"]="newConnection";
  DatosSerie["nodeId"]=nodeId;
  // DatosSerie["details"]= mesh.subConnectionJson(true);

  String DatosJSON;
  serializeJson(DatosSerie, DatosJSON);
  Serial.println(DatosJSON);
#ifndef SUPERVISOR
  mesh.sendSingle(supervisorName, DatosJSON);
#endif
}

void changedConnectionCallback() {
  nodes = mesh.getNodeList();
  String nombres;
  node = nodes.begin();
  nombres += (*node);
  while (node != nodes.end()) {
    nombres += " ";
    nombres += (*node);
    node++;
  }
  
  DynamicJsonDocument DatosSerie(1024);  
  DatosSerie.clear();
  DatosSerie["origin"]=NombreNodo;
  DatosSerie["timestamp"]=millis(); 
  DatosSerie["class"]="changedConnection"; 
  DatosSerie["nodes"]=nombres;

  String DatosJSON;
  serializeJson(DatosSerie, DatosJSON);
  Serial.println(DatosJSON);
#ifndef SUPERVISOR
  mesh.sendSingle(supervisorName, DatosJSON);
#endif
}

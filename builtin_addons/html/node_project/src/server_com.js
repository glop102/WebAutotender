import {ref,computed, watchPostEffect} from "vue";

export const workflows = ref({});
export const instances = ref({});
export const global_variables = ref({});


//===================================================================
// Instances
//===================================================================
export async function refresh_instances() {
    const response = await fetch("/api/instances");
    if(response.ok){
        instances.value = await response.json();
        // console.log(instances.value);
    }else {
        console.log("Unable to fetch the instances list");
    }
}
refresh_instances();

export async function refresh_instance(uuid) {
    const response = await fetch("/api/instances/" + uuid);
    if (response.ok) {
        const inst = await response.json();
        instances.value[uuid] = inst;
    } else {
        console.log("Unable to fetch the instance " + uuid);
        if(response.status === 404){
            delete instances.value[uuid];
        }
    }
}
export async function toggle_instance_pause(uuid) {
    const request = await fetch("/api/instances/" + uuid + "/toggle_pause", { method: "POST", cache: "no-cache" });
    if (request.ok) {
        await request.text();
        // refresh_instance(uuid);
    } else {
        console.log("Unable to toggle the running state for instance " + uuid);
    }
}
export function workflow_instances(workflow_uuid) {
    return computed(
        () => Object.fromEntries(
            Object.entries(instances.value)
                .filter((inst) => inst[1].workflow_uuid == workflow_uuid))
    )
}
export async function push_instance_state(uuid) {
    const response = await fetch("/api/instances/" + uuid,
        {
            method: "PUT",
            cache: "no-cache",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(instances.value[uuid])
        }
    );
    if (response.ok) {
        return true;
    } else {
        console.log("Unable to push Instance state " + uuid);
        return false;
    }
}
export async function delete_instance(uuid) {
    if (!confirm("Are you sure you want to delete the instance:\n" + uuid)) {
        return;
    }
    const response = await fetch("/api/instances/" + uuid,
        {
            method: "DELETE",
            cache: "no-cache"
        }
    );
    if (response.ok) {
        delete instances.value[uuid];
    } else {
        console.log("Unable to fetch the workflow " + uuid);
    }
}

//===================================================================
// Workflows
//===================================================================
export async function refresh_workflows() {
    const response = await fetch("/api/workflows");
    if(response.ok){
        workflows.value = await response.json();
        // console.log(workflows.value);
    }else{
        console.log("Unable to fetch the workflows list");
    }
}
refresh_workflows();

export async function refresh_workflow(workflow_uuid) {
    const response = await fetch("/api/workflows/"+workflow_uuid);
    if (response.ok) {
        const workflow = await response.json();
        workflows.value[workflow_uuid] = workflow;
    } else {
        console.log("Unable to fetch the workflow "+workflow_uuid);
        if(response.status === 404){
            delete workflows.value[workflow_uuid];
        }
    }
}
export async function toggle_workflow_pause(workflow_uuid) {
    const request = await fetch("/api/workflows/" + workflow_uuid + "/toggle_pause", { method: "POST", cache: "no-cache" });
    if (request.ok) {
        await request.text();
        // refresh_workflow(workflow_uuid);
    } else {
        console.log("Unable to toggle the running state for workflow " + workflow_uuid);
    }
}
export async function push_workflow_state(uuid) {
    const response = await fetch("/api/workflows/" + uuid,
        {
            method: "PUT",
            cache: "no-cache",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(workflows.value[uuid])
        }
    );
    if (response.ok) {
        return true;
    } else {
        console.log("Unable to push Workflow state " + uuid);
        return false;
    }
}
export async function delete_workflow(workflow_uuid) {
    if(!confirm("Are you sure you want to delete the workflow:\n"+workflow_uuid+"\n"+workflows.value[workflow_uuid].name)){
        return;
    }
    const request = await fetch("/api/workflows/" + workflow_uuid, { method: "DELETE", cache: "no-cache" });
    if (request.ok) {
        delete workflows.value[workflow_uuid];
    } else {
        console.log("Unable to delete the workflow " + workflow_uuid);
    }
}


//===================================================================
// Global Variabless
//===================================================================
export async function refresh_global_variables() {
    const response = await fetch("/api/global_variables");
    if (response.ok) {
        global_variables.value = await response.json();
        // console.log(workflows.value);
    } else {
        console.log("Unable to fetch the global variables list");
    }
}
refresh_global_variables();

export async function refresh_global_variable(varname) {
    const response = await fetch("/api/global_variables/" + varname);
    if (response.ok) {
        const gvar = await response.json();
        global_variables.value[varname] = gvar;
    } else {
        console.log("Unable to fetch the global variable " + varname);
        if (response.status === 404) {
            delete global_variables.value[varname];
        }
    }
}
export async function push_global_variable_state(varname) {
    const response = await fetch("/api/global_variables/" + varname,
        {
            method: "PUT",
            cache: "no-cache",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(global_variables.value[varname])
        }
    );
    if (response.ok) {
        return true;
    } else {
        console.log("Unable to push global variable state " + varname);
        return false;
    }
}
export async function delete_global_variable(varname) {
    if (!confirm("Are you sure you want to delete the variable:\n" + varname)) {
        return;
    }
    const request = await fetch("/api/global_variables/" + varname, { method: "DELETE", cache: "no-cache" });
    if (request.ok) {
        // delete global_variables.value[varname];
    } else {
        console.log("Unable to delete the global variable " + varname);
    }
}
export async function create_placeholder_global_variable(varname){
    if(varname == "") return;
    global_variables.value[varname] = {
        'value': "",
        'typename': "String"
    };
    push_global_variable_state(varname);
}

//===================================================================
// Orphans
//===================================================================
export const orphans = computed(
    () => Object.fromEntries(
        Object.entries(instances.value)
        .filter((inst) => !Object.keys(workflows.value).includes(inst[1].workflow_uuid))
    )
);



//===================================================================
// Instance Editor
//===================================================================
export const instance_edit_state = ref({"show":false,"uuid":""});
export function show_instance_edit(uuid){
    instance_edit_state.value = {
        "show":true,
        "uuid":uuid,
        "client_error_message": "",
        "tempspace": JSON.parse(JSON.stringify(instances.value[uuid])),
    }
}
export function close_instance_edit() {
    instance_edit_state.value = {
        "show": false,
        "uuid": ""
    }
}
export async function save_and_close_instance_edit(){
    instances.value[instance_edit_state.value.uuid] = instance_edit_state.value.tempspace;
    if(await push_instance_state(instance_edit_state.value.uuid)){
        close_instance_edit();
    }else{
        instance_edit_state.value.client_error_message = "Unable to push the instance state to the server";
    }
}

//===================================================================
// Spawn Instance Editor
//===================================================================
export const spawninstance_edit_state = ref({ "show": false, "workflow_uuid": "" });
export function show_spawninstance_edit(workflow_uuid) {
    spawninstance_edit_state.value = {
        "show": true,
        "workflow_uuid": workflow_uuid,
        "client_error_message": "",
        "tempspace": {}
    }
}
export function close_spawninstance_edit() {
    spawninstance_edit_state.value = {
        "show": false,
        "workflow_uuid": ""
    }
}
export async function save_and_close_spawninstance_edit() {
    const response = await fetch("/api/workflows/" + spawninstance_edit_state.value.workflow_uuid + "/spawn_instance",
        {
            method: "POST",
            cache: "no-cache",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(spawninstance_edit_state.value.tempspace)
        }
    );
    if (response.ok) {
        close_spawninstance_edit();
    } else {
        console.log("Unable to Spawn the new instance");
        spawninstance_edit_state.value.client_error_message = "Unable to Spawn the new instance";
    }
}


//===================================================================
// Workflow Editor
//===================================================================
export const workflow_edit_state = ref({ "show": false, "uuid": "" });
export function show_workflow_edit(uuid) {
    workflow_edit_state.value = {
        "show": true,
        "uuid": uuid,
        "client_error_message": "",
        "tempspace": JSON.parse(JSON.stringify(workflows.value[uuid])),
    }
}
export async function add_new_workflow_edit() {
    const uuid = await retrieve_random_uuid();
    if(!uuid) return;
    const default_workflow = {
        "name": "",
        "state": "Running",
        "uuid": uuid,
        "user_notes": "",
        "constants": {},
        "setup_variables": {},
        "procedures": {"start":[]}
    };
    workflow_edit_state.value = {
        "show": true,
        "uuid": uuid,
        "client_error_message": "",
        "tempspace": default_workflow,
    }
}
export function close_workflow_edit() {
    workflow_edit_state.value = {
        "show": false,
        "uuid": ""
    }
}
export async function save_and_close_workflow_edit() {
    if(workflow_edit_state.value.tempspace.name == ""){
        workflow_edit_state.value.tempspace.name = workflow_edit_state.value.uuid;
    }
    workflows.value[workflow_edit_state.value.uuid] = workflow_edit_state.value.tempspace;
    if(await push_workflow_state(workflow_edit_state.value.uuid)){
        close_workflow_edit();
    }else{
        workflow_edit_state.value.client_error_message = "Unable to push the workflow state to the server";
    }
}


//===================================================================
// Variables
//===================================================================
export const variable_types = ref([])
export async function refresh_variable_types(){
    const response = await fetch("/api/variable_types");
    if (response.ok) {
        variable_types.value = await response.json();
    } else {
        console.log("Unable to fetch the list of variable_types");
    }
}
refresh_variable_types();

//===================================================================
// Commands
//===================================================================
export const available_commands = ref([])
export const available_commands_names = computed(
    () => Object.keys(available_commands.value)
);
export async function refresh_available_commands() {
    const response = await fetch("/api/commands");
    if (response.ok) {
        available_commands.value = await response.json();
    } else {
        console.log("Unable to fetch the list of commands");
    }
}
refresh_available_commands();


//===================================================================
// Utils
//===================================================================
export async function retrieve_random_uuid() {
    const response = await fetch("/api/gen_uuid");
    if (response.ok) {
        return await response.json();
    } else {
        console.log("Unable to fetch a UUID");
        return null
    }
}


//===================================================================
// Server Events
//===================================================================

const serverEventConnection = ref(false);

const eventSource = new EventSource("/api/events_stream");
eventSource.onmessage = (event) => {
    console.log(event);
}
eventSource.addEventListener("RefreshInstance", (event) => {
    // console.log(event);
    refresh_instance(event.data);
});
eventSource.addEventListener("RefreshWorkflow", (event) => {
    // console.log(event);
    refresh_workflow(event.data);
});
eventSource.addEventListener("RefreshInstances", (event) => {
    // console.log(event);
    refresh_instances();
});
eventSource.addEventListener("RefreshWorkflows", (event) => {
    // console.log(event);
    refresh_workflows();
});
eventSource.addEventListener("RefreshGlobals", (event) => {
    // console.log(event);
    refresh_global_variables();
});
eventSource.addEventListener("RefreshGlobal", (event) => {
    // console.log(event);
    refresh_global_variable(event.data);
});
eventSource.addEventListener("DeleteInstance", (event) => {
    // console.log(event);
    delete instances.value[event.data];
});
eventSource.addEventListener("DeleteWorkflow", (event) => {
    // console.log(event);
    delete workflows.value[event.data];
});
eventSource.addEventListener("DeleteGlobal", (event) => {
    // console.log(event);
    delete global_variables.value[event.data];
});
eventSource.addEventListener("ClosingDown", (event) => {
    console.log("Disconnecting due to server shutting down");
    eventSource.close();
});
eventSource.onerror = (err) => { serverEventConnection.value = false; };
eventSource.onopen = (thing) => { serverEventConnection.value = true; };
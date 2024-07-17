import {ref,computed, watchPostEffect} from "vue";

export const workflows = ref({});
export const instances = ref({});


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
    }
}
export async function toggle_instance_pause(uuid) {
    const request = await fetch("/api/instances/" + uuid + "/toggle_pause", { method: "POST", cache: "no-cache" });
    if (request.ok) {
        await request.text();
        refresh_instance(uuid);
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
    } else {
        console.log("Unable to push Instance state " + uuid);
    }
}
export async function delete_instance(uuid) {
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
    }
}
export async function toggle_workflow_pause(workflow_uuid) {
    const request = await fetch("/api/workflows/" + workflow_uuid + "/toggle_pause", { method: "POST", cache: "no-cache" });
    if (request.ok) {
        await request.text();
        refresh_workflow(workflow_uuid);
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
    } else {
        console.log("Unable to push Workflow state " + uuid);
    }
}
export async function delete_workflow(workflow_uuid) {
    if(!confirm("Are you sure you want to delete the workflow:\n"+workflow_uuid)){
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
        "tempspace": JSON.parse(JSON.stringify(instances.value[uuid])),
    }
}
export function close_instance_edit() {
    instance_edit_state.value = {
        "show": false,
        "uuid": ""
    }
}
export function save_and_close_instance_edit(){
    // TODO Make this not just blindly push, but have it wait before closing the edit dialog and on failure of pushing, leave the edit dialog open
    instances.value[instance_edit_state.value.uuid] = instance_edit_state.value.tempspace;
    push_instance_state(instance_edit_state.value.uuid)
    close_instance_edit();
}


//===================================================================
// Workflow Editor
//===================================================================
export const workflow_edit_state = ref({ "show": false, "uuid": "" });
export function show_workflow_edit(uuid) {
    workflow_edit_state.value = {
        "show": true,
        "uuid": uuid,
        "tempspace": JSON.parse(JSON.stringify(workflows.value[uuid])),
    }
}
export function add_new_workflow_edit() {
    const default_workflow = {
        "name": "",
        "state": "Running",
        "uuid": "",
        "user_notes": "",
        "constants": {},
        "setup_variables": {},
        "procedures": {}
    };
}
export function close_workflow_edit() {
    workflow_edit_state.value = {
        "show": false,
        "uuid": ""
    }
}
export function save_and_close_workflow_edit() {
    // TODO Make this not just blindly push, but have it wait before closing the edit dialog and on failure of pushing, leave the edit dialog open
    workflows.value[workflow_edit_state.value.uuid] = workflow_edit_state.value.tempspace;
    push_workflow_state(workflow_edit_state.value.uuid)
    close_workflow_edit();
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
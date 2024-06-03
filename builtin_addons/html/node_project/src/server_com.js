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
        console.log("Unable to fetch the workflow " + workflow_name);
    }
}
export async function toggle_instance_pause(uuid) {
    const request = await fetch("/api/instances/" + uuid + "/toggle_pause", { method: "POST", cache: "no-cache" });
    if (request.ok) {
        await request.text();
        refresh_instance(uuid);
    } else {
        console.log("Unable to toggle the running state for workflow " + workflow_name);
    }
}
export function workflow_instances(workflow_name) {
    //Yeah, the name, and not the reference object of the workflow
    //The name of a workflow is effectivly the primary key of the workflow and thus is not allowed to be changed in the UI
    //If it ever changes, then it would orphan a bunch of instances. That also happens if it is deleted, but well, you are deleting things
    return computed(
        () => Object.fromEntries(
            Object.entries(instances.value)
                .filter((inst) => inst[1].workflow_name == workflow_name))
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
        console.log("Unable to fetch the workflow " + workflow_name);
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

export async function refresh_workflow(workflow_name) {
    const response = await fetch("/api/workflows/"+workflow_name);
    if (response.ok) {
        const workflow = await response.json();
        workflows.value[workflow_name] = workflow;
    } else {
        console.log("Unable to fetch the workflow "+workflow_name);
    }
}
export async function toggle_workflow_pause(workflow_name) {
    const request = await fetch("/api/workflows/" + workflow_name + "/toggle_pause", { method: "POST", cache: "no-cache" });
    if (request.ok) {
        await request.text();
        refresh_workflow(workflow_name);
    } else {
        console.log("Unable to toggle the running state for workflow " + workflow_name);
    }
}

//===================================================================
// Orphans
//===================================================================
export const workflow_names = computed(
    () => Object.keys(workflows.value)
);
export const orphans = computed(
    () => Object.fromEntries(
        Object.entries(instances.value)
        .filter((inst) => !workflow_names.value.includes(inst[1].workflow_name))
    )
);



//===================================================================
// Instance Editor
//===================================================================
export const instance_edit_state = ref({"show":false});
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
    }
}
export function save_and_close_instance_edit(){
    instances.value[instance_edit_state.value.uuid] = instance_edit_state.value.tempspace;
    push_instance_state(instance_edit_state.value.uuid)
    close_instance_edit();
}
import {ref,computed} from "vue";

export const workflows = ref({});
export const instances = ref({});

export async function refresh_instances() {
    const response = await fetch("/api/instances");
    if(response.ok){
        instances.value = await response.json();
        // console.log(instances.value);
    }else {
        console.log("Unable to fetch the instances list");
    }
}
export async function refresh_instance(uuid) {
    const response = await fetch("/api/instances/" + uuid);
    if (response.ok) {
        const inst = await response.json();
        instances.value[uuid] = inst;
    } else {
        console.log("Unable to fetch the workflow " + workflow_name);
    }
}
refresh_instances();

export async function refresh_workflows() {
    const response = await fetch("/api/workflows");
    if(response.ok){
        workflows.value = await response.json();
        // console.log(workflows.value);
    }else{
        console.log("Unable to fetch the workflows list");
    }
}
export async function refresh_workflow(workflow_name) {
    const response = await fetch("/api/workflows/"+workflow_name);
    if (response.ok) {
        const workflow = await response.json();
        workflows.value[workflow_name] = workflow;
    } else {
        console.log("Unable to fetch the workflow "+workflow_name);
    }
}
refresh_workflows();

export const workflow_names = computed(
    () => Object.keys(workflows.value)
);
export const orphans = computed(
    () => Object.fromEntries(
        Object.entries(instances.value)
        .filter((inst) => !workflow_names.value.includes(inst[1].workflow_name))
    )
);

export function workflow_instances(workflow_name){
    //Yeah, the name, and not the reference object of the workflow
    //The name of a workflow is effectivly the primary key of the workflow and thus is not allowed to be changed in the UI
    //If it ever changes, then it would orphan a bunch of instances. That also happens if it is deleted, but well, you are deleting things
    return computed(
        () => Object.fromEntries(
            Object.entries(instances.value)
            .filter((inst) => inst[1].workflow_name == workflow_name))
    )
}

export async function toggle_workflow_pause(workflow_name){
    const request = await fetch("/api/workflows/"+workflow_name+"/toggle_pause",{method:"POST",cache:"no-cache"});
    if(request.ok){
        await request.text();
        refresh_workflow(workflow_name);
    }else{
        console.log("Unable to toggle the running state for workflow "+workflow_name);
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
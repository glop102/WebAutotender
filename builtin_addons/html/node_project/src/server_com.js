import {ref,computed} from "vue";

export const workflows = ref([]);
export const instances = ref([]);

export async function refresh_instances() {
    const response = await fetch("/api/instances");
    if(response.ok){
        instances.value = await response.json();
    }else {
        console.log("Unable to fetch the instances list");
    }
}
refresh_instances();

export async function refresh_workflows() {
    const response = await fetch("/api/workflows");
    if(response.ok){
        workflows.value = await response.json();
    }else{
        console.log("Unable to fetch the instances list");
    }
}
refresh_workflows();

export const workflow_names = computed(
    ()=>workflows.value.map(a=>a.name)
);
export const orphans = computed(
    ()=>instances.value.filter(
        (item)=>!workflow_names.value.includes(item.workflow_name)
    )
);

export function workflow_instances(workflow_name){
    //Yeah, the name, and not the reference object of the workflow
    //The name of a workflow is effectivly the primary key of the workflow and thus is not allowed to be changed in the UI
    //If it ever changes, then it would orphan a bunch of instances. That also happens if it is deleted, but well, you are deleting things
    return computed(
        () => instances.value.filter(
            (item) => item.workflow_name == workflow_name
        )
    );
}
<script setup>
import Instance from "./Instance.vue"
import Procedure from "./Procedure.vue"
import Variable from "./Variable.vue";
import {ref,onMounted} from "vue"

const props = defineProps({
    workflow: Object
});
const show_details = ref(false);
const instances = ref([]);
function toggle_details_visibility(){
    show_details.value = !show_details.value;
}
function toggle_processing_state(){
    show_details.value = !show_details.value;
}

async function refresh_instances(){
    const response = await fetch("/api/workflows/"+props.workflow.name+"/instances");
    instances.value = await response.json();
}
onMounted(refresh_instances);
</script>

<template>
    <div class="workflow_details">
        <div class="workflow_details_name">{{ workflow.name }}</div>
        <button class="collapse_button" @click="toggle_details_visibility()">Details</button>
        <button type="button" class="workflow_details_state" @click="toggle_processing_state()">{{ workflow.state }}</button>
        <p class="workflow_details_user_notes" v-if="workflow.user_notes.length > 0">{{ workflow.user_notes }}</p>
        <div v-if="show_details">
            <div class="workflow_details_section_title">Constants:</div>
            <div class="workflow_details_constants">
                <Variable v-for="v in Object.keys(workflow.constants)" :key="v" :name="v" :variable="workflow.constants[v]"/>
            </div>
            <div class="workflow_details_section_title">SetupVariables:</div>
            <div class="workflow_details_setup_variables">
                <Variable v-for="v in Object.keys(workflow.setup_variables)" :key="v" :name="v" :variable="workflow.setup_variables[v]"/>
            </div>
            <div class="workflow_details_section_title">Procedures:</div>
            <div class="workflow_details_procedures">
                <Procedure v-for="v in Object.keys(workflow.procedures)" :key="v" :name="v" :commands="workflow.procedures[v]"/>
            </div>
        </div>
        <div class="workflow_details_instances">
            <Instance v-for="i in instances" :key="i.uuid" :instance="i"/>
        </div>
    </div>
</template>
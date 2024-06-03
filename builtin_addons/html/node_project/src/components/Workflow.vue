<script setup>
import Instance from "./Instance.vue"
import Procedure from "./Procedure.vue"
import Variable from "./Variable.vue";
import {ref} from "vue"
import { workflow_instances } from "@/server_com";

const props = defineProps({
    workflow: Object
});
const instances = workflow_instances(props.workflow.name);

const show_details = ref(false);
function toggle_details_visibility(){
    show_details.value = !show_details.value;
}
function toggle_processing_state(){
    show_details.value = !show_details.value;
}
</script>

<style>
.workflow_details_constants,
.workflow_details_setup_variables,
.workflow_details_procedures {
    padding-left: 1em;
}

.workflow_details_name{
    margin-top: 0;
    margin-bottom: 0;
    display: inline;
}

.workflow_details_section_title {
    margin-top: 0;
    margin-bottom: 0;
    display: inline;
}
</style>

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
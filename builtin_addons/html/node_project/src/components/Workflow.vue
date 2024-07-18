<script setup>
import Instance from "./Instance.vue"
import Procedure from "./Procedure.vue"
import Variable from "./Variable.vue";
import {ref} from "vue"
import { workflow_instances,toggle_workflow_pause,show_workflow_edit,delete_workflow,show_spawninstance_edit } from "@/server_com";

const props = defineProps({
    workflow: Object
});
const instances = workflow_instances(props.workflow.uuid);

const show_details = ref(false);
function toggle_details_visibility(){
    show_details.value = !show_details.value;
}
</script>

<style>
.workflow_details_constants,
.workflow_details_setup_variables {
    padding-left: 1em;
}
.workflow_details_procedures {
    padding-left: 1em;
    display: flex;
}

.workflow_details_name {
    font-size: 1em;
}
.workflow_details_section_title {
    margin-top: 0;
    margin-bottom: 0;
    display: inline;
}

.workflow_details_collapsable {
    border-left: solid 0.1em;
    padding-left: 1em;
}
.workflow_details_instances{
    display: flex;
}
</style>

<template>
    <div class="workflow_details">
        <button class="workflow_details_name" @click="toggle_details_visibility()">{{ workflow.name }}</button>
        <button type="button" class="workflow_details_state" @click="toggle_workflow_pause(workflow.uuid)">{{ workflow.state }}</button>
        -
        <button type="button" class="workflow_details_spawn_instance" @click="show_spawninstance_edit(props.workflow.uuid)">Spawn Instance</button>
        <div v-if="show_details">
            <button type="button" @click="show_workflow_edit(workflow.uuid)">Edit</button>
            <button type="button" @click="delete_workflow(workflow.uuid)">Delete</button>
        </div>
        <p class="workflow_details_user_notes" v-if="workflow.user_notes.length > 0">{{ workflow.user_notes }}</p>
        <div v-if="show_details" class="workflow_details_collapsable">
            <div>UUID: {{ workflow.uuid }}</div>
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
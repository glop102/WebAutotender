<script setup>
import Instance from './components/Instance.vue'
import Workflow from './components/Workflow.vue'
import GlobalVariable from './components/GlobalVariable.vue'

import InstanceEdit from './components/InstanceEdit.vue'
import WorkflowEdit from './components/WorkflowEdit.vue'
import SpawnInstance from './components/SpawnInstance.vue'

import { global_variables, orphans,workflows } from './server_com';
import { instance_edit_state,workflow_edit_state,spawninstance_edit_state,add_new_workflow_edit,create_placeholder_global_variable } from './server_com';

import {ref} from 'vue';

const global_new_varname = ref('');
async function make_new_global_var(){
    await create_placeholder_global_variable(global_new_varname.value);
    global_new_varname.value='';
}
</script>

<style>
.workflow_list, .orphan_instance_list {
    display: flex;
    flex-wrap: wrap;
    padding: 1em;
}
.workflow_add_new_button{
    float: left;
}
</style>

<template>
    <header>
        <h1>Workflow Management</h1>
        <div id="summary_status"></div>
    </header>
    <main>
        <h2>Workflows</h2>
        <button type="button" @click="add_new_workflow_edit" class="workflow_add_new_button">+</button>
        <section id="workflow_list">
            <Workflow v-for="w in workflows" :key="w.uuid" :workflow="w" />
        </section>
        <h2 v-if="Object.keys(orphans).length>0">Orphan Instances</h2>
        <section id="orphan_instance_list" v-if="Object.keys(orphans).length>0">
            <Instance v-for="inst in orphans" :key="inst.uuid" :instance="inst" />
        </section>
        <h2>Globals</h2>
        <input placeholder="variable name" v-model="global_new_varname" />
        <button type="button" class="globals_add_new_button" @click="make_new_global_var">+</button>
        <section>
            <GlobalVariable v-for="vname in Object.keys(global_variables)" :key="vname" :varname="vname" />
        </section>
        <!-- The Edit components use a *copy* of what is being edited so that it can be mutated and then thrown away on a cancel. Check server_com for the copies -->
        <InstanceEdit v-if="instance_edit_state.show" />
        <WorkflowEdit v-if="workflow_edit_state.show" />
        <SpawnInstance v-if="spawninstance_edit_state.show" />
    </main>
    <footer>
        <a href="https://github.com/glop102/WebAutotender">github</a>
    </footer>
</template>
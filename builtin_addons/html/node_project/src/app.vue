<script setup>
import Instance from './components/Instance.vue'
import Workflow from './components/Workflow.vue'

import InstanceEdit from './components/InstanceEdit.vue'
import WorkflowEdit from './components/WorkflowEdit.vue'
import SpawnInstance from './components/SpawnInstance.vue'

import { orphans,workflows } from './server_com';
import { instance_edit_state,workflow_edit_state,spawninstance_edit_state,add_new_workflow_edit } from './server_com';
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
        <!-- TODO: A section for global variables -->
        <h2>Workflows</h2>
        <button type="button" @click="add_new_workflow_edit" class="workflow_add_new_button">+</button>
        <section id="workflow_list">
            <Workflow v-for="w in workflows" :key="w.uuid" :workflow="w" />
        </section>
        <h2>Orphan Instances</h2>
        <section id="orphan_instance_list">
            <Instance v-for="inst in orphans" :key="inst.uuid" :instance="inst" />
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
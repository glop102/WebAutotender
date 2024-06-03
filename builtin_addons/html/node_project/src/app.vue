<script setup>
import Instance from './components/Instance.vue'
import Workflow from './components/Workflow.vue'

import InstanceEdit from './components/InstanceEdit.vue'

import { orphans,workflows } from './server_com';
import { instance_edit_state } from './server_com';
</script>

<style>
.workflow_list, .orphan_instance_list {
    display: flex;
    flex-wrap: wrap;
    padding: 1em;
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
        <section id="workflow_list">
            <Workflow v-for="w in workflows" :key="w.name" :workflow="w" />
        </section>
        <h2>Orphan Instances</h2>
        <section id="orphan_instance_list">
            <Instance v-for="inst in orphans" :key="inst.uuid" :instance="inst" />
        </section>
        <InstanceEdit v-if="instance_edit_state.show" />
    </main>
    <footer>
        <a href="https://github.com/glop102/WebAutotender">github</a>
    </footer>
</template>
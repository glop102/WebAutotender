<script setup>
import Instance from './components/Instance.vue'
import Workflow from './components/Workflow.vue'

import { orphans,workflows } from './server_com';
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
        <h2>Workflows</h2>
        <section id="workflow_list">
            <Workflow v-for="w in workflows" :key="w.name" :workflow="w" />
        </section>
        <h2>Orphan Instances</h2>
        <section id="orphan_instance_list">
            <Instance v-for="inst in orphans" :key="inst.uuid" :instance="inst" />
        </section>
    </main>
    <footer>
        <a href="https://github.com/glop102/WebAutotender">github</a>
    </footer>
</template>
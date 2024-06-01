<script setup>
import Instance from './components/Instance.vue'
import Workflow from './components/Workflow.vue'
import {ref} from 'vue'

const workflows = ref([]);
const orphans = ref([]);

async function refresh_orphans(){
    const response = await fetch("/api/instances/orphans");
    orphans.value = await response.json();
}
refresh_orphans();

async function refresh_workflows(){
    const response = await fetch("/api/workflows");
    workflows.value = await response.json();
}
refresh_workflows();
</script>

<style>
.workflow_list, .orphan_instance_list {
    display: flex;
    flex-wrap: wrap;
    padding: 1em;
}
</style>

<template>
    <h2>Workflows</h2>
    <section id="workflow_list">
        <Workflow v-for="w in workflows" :key="w.name" :workflow="w" />
    </section>
    <h2>Orphan Instances</h2>
    <section id="orphan_instance_list">
        <Instance v-for="inst in orphans" :key="inst.uuid" :instance="inst" />
    </section>
</template>
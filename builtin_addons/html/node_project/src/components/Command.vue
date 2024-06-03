<script setup>
import Variable from './Variable.vue';
const props = defineProps({
    command: Object
});
</script>

<style>
.command_details {
    /* border: solid 0.1em;
                padding: 0.5em;
                margin: 0.25em;
                border-radius: 1em; */
    padding: 0.5em;
}

.command_details_variables {
    display: inline-block;
}
</style>

<template>
    <div class="command_details">
        <div class="command_details_name">{{ command.command_name }}</div>
        <div class="command_details_variables">
            <Variable v-for="v in Object.keys(command.variables)" :key="v" :name="v" :variable="command.variables[v]"/>
        </div>
    </div>
</template>
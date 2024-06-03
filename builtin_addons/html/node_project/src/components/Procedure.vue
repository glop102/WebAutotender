<script setup>
import Command from "./Command.vue";
const props = defineProps({
    name: String,
    commands: Array
});
</script>

<style>
.procedure_details {
    display: block;
    border: solid 0.1em;
    padding: 0.5em;
    margin: 0.25em;
    border-radius: 0.25em;
    width: fit-content;
}
</style>

<template>
    <div class="procedure_details">
        <div class="procedure_details_name">{{ name }}</div>
        <div class="procedure_details_commands">
            <Command v-for="(c,idx) in commands" :command="c" :class="{'list_odd_item':idx%2==1}" />
        </div>
    </div>
</template>
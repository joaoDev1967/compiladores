int main() {
    for (int i = 0; i < 3; i++) { int z = i; }
    i = 9; // erro semantico intencional: i nao existe fora do for
    return 0;
}

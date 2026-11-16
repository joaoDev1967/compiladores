int exemplo(int *a) {
    int x = a; // erro intencional: ponteiro nao e escalar
    int xs[3];
    xs = 1; // erro intencional: array nao recebe inteiro
    return x;
}
